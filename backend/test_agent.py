"""Agent wiring checks with a scripted stand-in model (no API key or network needed).

    cd backend && python test_agent.py

A real model is exercised by asking the chat widget, or POST /api/chat.
"""
import os as _os, tempfile as _tf; _os.environ.setdefault("CAMPUS_CUSTOMS_AUDIT", _os.path.join(_tf.mkdtemp(), "audit_trail.json"))  # tests never touch the real audit trail

import asyncio

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

import agent
import tools
from models import ChatTurn

results = []


def check(name: str, cond: bool) -> None:
    results.append(cond)
    print(("PASS " if cond else "FAIL ") + name)


def tool_returns(messages: list[ModelMessage]) -> list[ToolReturnPart]:
    return [p for m in messages for p in getattr(m, "parts", []) if isinstance(p, ToolReturnPart)]


def scripted(invent_first: bool = False):
    """Search for hoodies, optionally reply once with a made-up id, then reply with a real one."""
    state = {"invented": False}

    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        returns = tool_returns(messages)
        if not returns:
            return ModelResponse(parts=[ToolCallPart("search_products", {"query": "hoodie", "size": "XL"})])
        real_id = returns[0].content.products[0].product_id
        out = info.output_tools[0].name
        if invent_first and not state["invented"]:
            state["invented"] = True
            return ModelResponse(parts=[ToolCallPart(out, {"message": "Try this!", "product_ids": ["pink-unicorn-hoodie"]})])
        return ModelResponse(parts=[ToolCallPart(out, {"message": "Here's a hoodie in XL.", "product_ids": [real_id]})])

    return FunctionModel(fn)


async def main() -> None:
    check("system prompt loaded from prompts/prompt.md", "Campus Customs Stylist" in agent.PROMPT_PATH.read_text(encoding="utf-8"))

    agent._model = scripted()
    out = await agent.run_chat("Any hoodies in XL?", [])
    reply = out.reply
    check("agent calls search_products", out.tool_log == ["search_products"])
    check("agent returns a ShopReply with a real product id", reply.message and len(reply.product_ids) == 1)

    agent._model = scripted(invent_first=True)
    reply = (await agent.run_chat("Any hoodies in XL?", [])).reply
    check("made-up product id is rejected and the model retries", "pink-unicorn-hoodie" not in reply.product_ids and len(reply.product_ids) == 1)

    # History: earlier cards count as already shown; fake ids from the browser are dropped
    seen = {}

    def remember(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen["text"] = " ".join(str(getattr(p, "content", "")) for m in messages for p in m.parts)
        out = info.output_tools[0].name
        return ModelResponse(parts=[ToolCallPart(out, {"message": "Yes!", "product_ids": ["basic-hoodie-big-yale"]})])

    agent._model = FunctionModel(remember)
    history = [
        ChatTurn(role="user", content="hoodies?"),
        ChatTurn(role="assistant", content="Here are two.", product_ids=["basic-hoodie-big-yale", "fake-id"]),
    ]
    reply = (await agent.run_chat("is the first one in M?", history)).reply
    check("earlier product cards reach the model", "basic-hoodie-big-yale" in seen["text"])
    check("fake product ids in history are dropped", "fake-id" not in seen["text"])
    check("a product shown earlier can be shown again without a new search", reply.product_ids == ["basic-hoodie-big-yale"])

    # Problem 7: a browsing question puts ALL of a search's matches on the page
    def browse(bad_id_first: bool):
        state = {"bad": bad_id_first}

        def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            returns = tool_returns(messages)
            if not returns:
                return ModelResponse(parts=[ToolCallPart("search_products", {"query": "hoodie"})])
            sr = returns[0].content
            out_tool = info.output_tools[0].name
            page_id = "search_99" if state["bad"] else sr.search_id
            state["bad"] = False
            return ModelResponse(parts=[ToolCallPart(out_tool, {
                "message": f"We have {sr.total_matches} hoodies!", "product_ids": [sr.products[0].product_id],
                "page_search_id": page_id, "page_title": "Hoodies"})])

        return FunctionModel(fn)

    agent._model = browse(bad_id_first=False)
    out = await agent.run_chat("What hoodies do you have?", [])
    full = tools.search_products("hoodie")[1]
    check("page gets every match, not just the 8 the model saw",
          out.page_search is not None and out.page_search.product_ids == full and len(full) > 8)
    check("page title comes from the agent", out.reply.page_title == "Hoodies")

    agent._model = browse(bad_id_first=True)
    out = await agent.run_chat("What hoodies do you have?", [])
    check("unknown page_search_id is rejected and retried", out.reply.page_search_id == "search_1" and out.page_search is not None)

    # Through the API: page_results arrive as full cards, and every card's detail record exists
    from fastapi.testclient import TestClient

    import main

    agent._model = browse(bad_id_first=False)
    with TestClient(main.app) as c:
        data = c.post("/api/chat", json={"message": "What hoodies do you have?", "history": []}).json()
        page = data.get("page_results") or {}
        cards = page.get("products", [])
        check("POST /api/chat returns page_results with every hoodie", page.get("total_matches") == len(full) == len(cards))
        check("page cards carry image, name, price and short info",
              all(k["image_url"].startswith("/media/card/") and k["name"] and k["price"] > 0 and k["description"] for k in cards))
        check("every page card opens a real detail record (/api/products/{id})",
              all(c.get(f"/api/products/{k['product_id']}").status_code == 200 for k in cards))

    print(f"\n{sum(results)}/{len(results)} passed")
    raise SystemExit(0 if all(results) else 1)


asyncio.run(main())
