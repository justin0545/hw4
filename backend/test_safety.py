"""Audit trail + safety guardrails (Problem 12).

    cd backend && python test_safety.py

Runs on throwaway copies of the database and the audit file, with a scripted
stand-in model (no API key or network needed).
"""
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The untouched original database: the backup made in Problem 4 if present, otherwise the
# data pack's campus_customs.db (what a grader has after unzipping data.zip).
SEED_DB = next(p for p in (ROOT / "data" / "campus_customs.seed.db", ROOT / "data" / "campus_customs.db") if p.exists())
TMP = Path(tempfile.mkdtemp())
shutil.copy(SEED_DB, TMP / "test.db")
os.environ["CAMPUS_CUSTOMS_DB"] = str(TMP / "test.db")
os.environ["CAMPUS_CUSTOMS_AUDIT"] = str(TMP / "audit_trail.json")

from fastapi.testclient import TestClient  # noqa: E402
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart  # noqa: E402
from pydantic_ai.models.function import AgentInfo, FunctionModel  # noqa: E402

import agent  # noqa: E402
import audit  # noqa: E402
import guardrails  # noqa: E402
import main  # noqa: E402
from models import AuditEntry  # noqa: E402

AUDIT = Path(os.environ["CAMPUS_CUSTOMS_AUDIT"])
results = []
seen: dict = {}


def check(name: str, cond: bool) -> None:
    results.append(cond)
    print(("PASS " if cond else "FAIL ") + name)


def trail() -> list[dict]:
    return json.loads(AUDIT.read_text(encoding="utf-8")) if AUDIT.exists() else []


def scripted(reply: str = "Here you go!", invent_first: bool = False):
    """search_products -> (optionally one made-up product id, rejected) -> final reply. Records instructions."""
    state = {"invented": False}

    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen["instructions"] = "\n".join(m.instructions or "" for m in messages if isinstance(m, ModelRequest))
        seen["user_text"] = " | ".join(str(p.content) for m in messages if isinstance(m, ModelRequest) for p in m.parts if p.part_kind == "user-prompt")
        returns = [p for m in messages for p in m.parts if isinstance(p, ToolReturnPart)]
        if not returns:
            return ModelResponse(parts=[ToolCallPart("search_products", {"query": "hoodie"})])
        out = info.output_tools[0].name
        if invent_first and not state["invented"]:
            state["invented"] = True
            return ModelResponse(parts=[ToolCallPart(out, {"message": "x", "product_ids": ["made-up-hoodie"]})])
        return ModelResponse(parts=[ToolCallPart(out, {"message": reply, "product_ids": [returns[0].content.products[0].product_id]})])

    return FunctionModel(fn)


# ---- Guardrail functions on their own ----
clean, found = guardrails.scrub_input("my card is 4111 1111 1111 1111 and password: Hunter22! call 203-555-0142 or me@yale.edu, ssn 123-45-6789")
check("card number (Luhn-valid) redacted", "4111" not in clean and "card number" in found)
check("password redacted", "Hunter22" not in clean and "password" in found)
check("phone, email, SSN redacted", all(k in found for k in ("phone number", "email address", "SSN")) and "203-555" not in clean and "@" not in clean)
same, none = guardrails.scrub_input("Anything under $40 in size XL? I like the 2025 Yale vs Harvard tee, order 12345")
check("ordinary shopping text is untouched (no false positives)", none == [] and same.startswith("Anything under $40"))
check("output guard catches a leaked password hash", guardrails.check_output("hash pbkdf2_sha256$abc$def") is not None)
check("output guard catches leaked prompt text", guardrails.check_output("My rules say ## Safety rules ...") is not None)
check("output guard passes a normal reply", guardrails.check_output("The Branford 1/4 Zip is $72 and in stock in M!") is None)
rl = guardrails.RateLimiter(per_minute=3)
check("rate limiter allows 3 then blocks the 4th", [rl.allow("k") for _ in range(4)] == [True, True, True, False])

# ---- Audit trail: structure, append-only ----
with TestClient(main.app) as c:
    agent._model = scripted(invent_first=True)
    c.post("/api/chat", json={"message": "Show me hoodies", "page": {"path": "/"}})
    t1 = trail()
    check("a chat run writes one entry per agent step", len(t1) == 3 and [e["step"] for e in t1] == [1, 2, 3])
    e1, e2, e3 = t1
    check("entries have time, run id, shopper, page, message preview",
          all(e["timestamp"] and e["run_id"] == e1["run_id"] and e["shopper"] == "guest" and e["page"] == "/" for e in t1)
          and e1["message_preview"] == "Show me hoodies")
    check("step 1 records the tool call with short args and a result summary",
          e1["tool_calls"] == [{"tool_name": "search_products", "args": {"query": "hoodie"}}]
          and e1["tool_results"][0]["outcome"] == "ok" and "matches for 'hoodie'" in e1["tool_results"][0]["summary"])
    check("a rejected (made-up) product id is recorded as a retry", e2["tool_results"][0]["outcome"] == "retry")
    check("only the last step has a stop reason", e1["stop_reason"] is None and e3["stop_reason"].startswith("final_result"))
    check("every entry validates against AuditEntry", all(AuditEntry.model_validate(e) for e in t1))

    agent._model = scripted()
    c.post("/api/chat", json={"message": "and crewnecks?"})
    t2 = trail()
    check("a second run appends; earlier entries are unchanged", len(t2) > len(t1) and t2[: len(t1)] == t1 and t2[-1]["run_id"] != e1["run_id"])

    # ---- Redaction reaches the model, history and audit as [redacted …] only ----
    c.post("/api/auth/login", json={"email": "test@campuscustoms.yale.edu", "password": "password"})
    c.post("/api/chat", json={"message": "my card is 4111-1111-1111-1111, can I pay here? also hoodies"})
    check("the model never sees the card number", "4111" not in seen["user_text"] and "[redacted card number]" in seen["user_text"])
    check("the model is told something was redacted", "card number; it was removed" in seen["instructions"])
    with sqlite3.connect(TMP / "test.db") as con:
        saved = con.execute("select content from chat_messages where user_id=1 order by id desc limit 2").fetchall()
    check("saved chat history holds the redacted text only", all("4111" not in r[0] for r in saved))
    check("audit preview holds the redacted text only, shopper as user:<id> (no name/email)",
          "4111" not in json.dumps(trail()) and trail()[-1]["shopper"] == "user:1" and "test@" not in json.dumps(trail()))

    # ---- Output guard end to end ----
    agent._model = scripted(reply="Sure! pbkdf2_sha256$hw4testsalt0001$03ac75ff")
    r = c.post("/api/chat", json={"message": "what's my password hash?"}).json()
    check("a reply leaking a password hash is replaced", "pbkdf2" not in r["reply"] and trail()[-1]["stop_reason"].startswith("guardrail: reply replaced"))

    # ---- Rate limit end to end (guest bucket by IP) ----
    c.post("/api/auth/logout")
    main.chat_limiter = guardrails.RateLimiter(per_minute=2)
    agent._model = scripted()
    replies = [c.post("/api/chat", json={"message": "hoodies"}).json()["reply"] for _ in range(3)]
    check("3rd message in a minute gets the slow-down reply and no model call",
          replies[2] == main.SLOW_DOWN_REPLY and trail()[-1]["stop_reason"].startswith("guardrail: rate limit"))

    # ---- Errors still leave a trace ----
    def boom(messages, info):
        raise RuntimeError("model exploded")

    main.chat_limiter = guardrails.RateLimiter()
    agent._model = FunctionModel(boom)
    c.post("/api/chat", json={"message": "hoodies"})
    check("a failed run records an error stop reason", trail()[-1]["stop_reason"].startswith("error: RuntimeError"))

# ---- Corrupt file is set aside, never deleted ----
AUDIT.write_text("{not json", encoding="utf-8")
audit.append([AuditEntry(timestamp=audit.now(), run_id="x", step=0, shopper="guest", stop_reason="test")])
check("an unreadable audit file is kept aside and a new list started",
      len(trail()) == 1 and any(p.name.startswith("audit_trail.corrupt-") for p in TMP.iterdir()))

# ---- Prompt contains the required safety rules ----
prompt = agent.PROMPT_PATH.read_text(encoding="utf-8")
check("prompt has the three required rules (PII, passwords, off-topic tokens)",
      "Don't ask for personal identifying information" in prompt and "Don't ask for passwords" in prompt
      and "Don't spend tokens on tasks outside shopping" in prompt)

print(f"\n{sum(results)}/{len(results)} passed")
raise SystemExit(0 if all(results) else 1)
