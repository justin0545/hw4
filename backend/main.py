"""Campus Customs API (FastAPI).

Problem 3: product catalogue, inventory and images from data/campus_customs.db.
Problem 4: create-account / login (auth.py).
Problem 5: the shop chatbot, a PydanticAI agent (agent.py) at POST /api/chat.
Problem 7: chat searches can fill the web page (ChatReply.page_results).
Problem 8: customer memory (chat_store.py) and page context for the agent.
Problem 9: My Closet + Wish List (shopper_lists.py), recommendations (recommend.py),
           compressed images (images.py).
Problem 12: audit trail (audit.py) and code-level safety guardrails (guardrails.py).

Run from the backend/ folder:
    uvicorn main:app --reload --port 8000
"""
import logging
from contextlib import asynccontextmanager

import asyncio

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic_ai.exceptions import ModelHTTPError

import agent
import audit
import chat_store
import guardrails
import images
import recommend
import shopper_lists
import tools
from auth import current_user, init_auth_tables, router as auth_router
from db import DATA_DIR
from models import (
    MAX_PAGE_RESULTS,
    ChatHistory,
    ChatReply,
    ChatRequest,
    ListAddRequest,
    AuditEntry,
    ListItem,
    PageResults,
    Recommendations,
)

log = logging.getLogger("campus_customs")
if not log.handlers:  # uvicorn only sets up its own loggers, so give ours a handler
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s: %(message)s"))
    log.addHandler(_handler)
    log.setLevel(logging.INFO)
    log.propagate = False

SLOW_DOWN_REPLY = "Whoa, that's a lot of messages at once! Give me a few seconds and try again. 🐾"
SAFE_FALLBACK_REPLY = "Sorry, I can't share that. I'm happy to help you find Yale gear, check sizes or put together an outfit!"
chat_limiter = guardrails.RateLimiter()

BLOCKED_REPLY = (
    "I'm just here to help you shop Campus Customs! Ask me about hoodies, crewnecks, tees, "
    "sizes or what's in stock, and I'll find something to show off your Yale pride."
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_auth_tables()
    chat_store.init_chat_tables()
    shopper_lists.init_list_tables()
    written = await asyncio.to_thread(images.ensure_images)  # only missing/stale files; ~0.3 s when up to date
    if written:
        log.info("images: built %d compressed product images", written)
    yield


app = FastAPI(title="Campus Customs API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
# Catalogue image_file_path values look like "products/<slug>.jpg". Only the
# products folder is served so the database file itself is never downloadable.
app.mount("/media/products", StaticFiles(directory=DATA_DIR / "products"), name="media")
# Compressed versions (images.py): /media/card/..., /media/large/..., /media/model/...
for _variant in images.VARIANTS:
    (images.OUT_DIR / _variant).mkdir(parents=True, exist_ok=True)
    app.mount(f"/media/{_variant}", StaticFiles(directory=images.OUT_DIR / _variant), name=f"media-{_variant}")


@app.middleware("http")
async def cache_images(request: Request, call_next):
    """Let browsers keep product images for a week instead of re-downloading them on every page."""
    response = await call_next(request)
    if request.url.path.startswith("/media/") and response.status_code == 200:
        response.headers["Cache-Control"] = "public, max-age=604800"
    return response


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "agent_model": agent.model_name, "api_key": tools.load_credentials() != "not found"}


# ---- Products ----------------------------------------------------------------

@app.get("/api/products")
def list_products() -> list[dict]:
    return tools.load_products()


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    products = tools.load_products(product_id)
    if not products:
        raise HTTPException(status_code=404, detail="Product not found")
    return products[0]


# ---- Chat ---------------------------------------------------------------------

def _page_results(search: agent.PageSearch | None, title: str | None) -> PageResults | None:
    """The agent's chosen search as cards for the page, in the search's ranking (Problem 7)."""
    if search is None or not search.product_ids:
        return None
    return PageResults(
        title=(title or "").strip() or f"Results for \"{search.query}\"",
        query=search.query,
        filters=search.filters,
        total_matches=len(search.product_ids),
        products=tools.product_cards(search.product_ids, limit=MAX_PAGE_RESULTS),
    )


@app.post("/api/chat")
async def chat(body: ChatRequest, request: Request) -> ChatReply:
    user = current_user(request)
    shopper = f"user:{user['id']}" if user else "guest"

    # Guardrail 1: rate limit per shopper (or per IP for guests).
    key = shopper if user else f"ip:{request.client.host if request.client else '?'}"
    if not chat_limiter.allow(key):
        audit.append([AuditEntry(timestamp=audit.now(), run_id="-", step=0, shopper=shopper,
                                 stop_reason="guardrail: rate limit (too many messages in a minute), no model call")])
        return ChatReply(reply=SLOW_DOWN_REPLY)

    # Guardrail 2: redact card numbers, SSNs, passwords, phones and emails before anything sees them.
    message, redacted = guardrails.scrub_input(body.message.strip())
    notes = [guardrails.redaction_note(redacted)] if redacted else []
    # Logged in: memory is the saved history in the database (the browser's copy is
    # ignored, so it can't be edited to put words in the assistant's mouth).
    # Guest: the browser's in-memory history, which isn't saved anywhere.
    customer = agent.Customer.from_user(user) if user else None
    history = chat_store.load_for_agent(user["id"]) if user else body.history
    page = agent.build_page_view(body.page)
    try:
        outcome = await agent.run_chat(message, history, customer=customer, page=page, safety_notes=notes)
    except tools.MissingAPIKey:
        log.error("Chat unavailable: PORTKEY_API_KEY is not set")
        raise HTTPException(503, "The shop assistant isn't set up yet (missing AI model key).")
    except ModelHTTPError as exc:
        if "content_filter" not in str(exc.body):
            log.exception("Model request failed")
            raise HTTPException(502, "Sorry, the shop assistant hit a snag. Please try again in a moment.")
        # The gateway's safety filter (Azure) blocked the message, e.g. a jailbreak attempt.
        # Not saved: a blocked message in the history would be re-sent, and blocked, every turn.
        log.warning("chat: message blocked by the model provider's content filter")
        return ChatReply(reply=BLOCKED_REPLY)
    except Exception:
        log.exception("Agent run failed")
        raise HTTPException(502, "Sorry, the shop assistant hit a snag. Please try again in a moment.")

    shop_reply = outcome.reply
    # Guardrail 3: never show a reply that leaks secrets (password hash, API key, system prompt, card number).
    leak = guardrails.check_output(shop_reply.message)
    if leak:
        log.warning("chat: reply blocked by output guard (%s)", leak)
        audit.append([AuditEntry(timestamp=audit.now(), run_id="-", step=0, shopper=shopper,
                                 message_preview=audit.clip(message, 160),
                                 stop_reason=f"guardrail: reply replaced by output guard ({leak})")])
        return ChatReply(reply=SAFE_FALLBACK_REPLY)
    reply = ChatReply(
        reply=shop_reply.message,
        products=tools.product_cards(shop_reply.product_ids),
        page_results=_page_results(outcome.page_search, shop_reply.page_title),
    )
    log.info("chat: user=%s page=%s tools=%s cards=%s page_results=%s", user and user["id"],
             page and (page.page_type, page.product and page.product.product_id), outcome.tool_log,
             [c.product_id for c in reply.products],
             reply.page_results and (reply.page_results.title, reply.page_results.total_matches))
    if user:
        chat_store.save_turn(user["id"], message, reply)
    return reply


@app.get("/api/chat/history")
def chat_history(request: Request) -> ChatHistory:
    """A returning logged-in shopper's saved conversation (last 50 messages). Empty for guests."""
    user = current_user(request)
    if not user:
        return ChatHistory(logged_in=False)
    return ChatHistory(logged_in=True, messages=chat_store.load_for_display(user["id"]))


# ---- My Closet, Wish List, recommendations (Problem 9) -------------------------

def _require_user(request: Request) -> dict:
    user = current_user(request)
    if not user:
        raise HTTPException(401, "Please log in to use your closet and wish list.")
    return user


def _list_kind(kind: str) -> str:
    if kind not in shopper_lists.LISTS:
        raise HTTPException(404, "Not found")
    return kind


@app.get("/api/me/{kind}")
def get_list(kind: str, request: Request) -> list[ListItem]:
    """kind = closet | wishlist"""
    return shopper_lists.list_items(_list_kind(kind), _require_user(request)["id"])


@app.post("/api/me/{kind}", status_code=201)
def add_to_list(kind: str, body: ListAddRequest, request: Request) -> ListItem:
    user = _require_user(request)
    try:
        return shopper_lists.add_item(_list_kind(kind), user["id"], body.product_id, body.size)
    except KeyError:
        raise HTTPException(404, "Product not found")
    except ValueError:
        raise HTTPException(422, "Sizes are XS, S, M, L, XL and XXL.")


@app.delete("/api/me/{kind}/{item_id}")
def remove_from_list(kind: str, item_id: int, request: Request) -> dict:
    if not shopper_lists.remove_item(_list_kind(kind), _require_user(request)["id"], item_id):
        raise HTTPException(404, "Item not found")
    return {"ok": True}


@app.post("/api/me/wishlist/{item_id}/move-to-closet")
def wishlist_to_closet(item_id: int, request: Request) -> ListItem:
    """'I bought it': moves a wish-list item into the closet."""
    item = shopper_lists.move_to_closet(_require_user(request)["id"], item_id)
    if item is None:
        raise HTTPException(404, "Item not found")
    return item


@app.get("/api/recommendations")
def recommendations(request: Request, limit: int = 8) -> Recommendations:
    """Personal picks from closet, wish list and chat history; staff picks for guests."""
    user = current_user(request)
    return recommend.recommend(user["id"] if user else None, limit=max(1, min(limit, 24)))


@app.get("/api/products/{product_id}/outfit")
def product_outfit(product_id: str, request: Request) -> dict:
    """'Complete the look' on the product page (Problem 10): same outfit logic as the stylist's suggest_outfit tool."""
    user = current_user(request)
    owned = set(shopper_lists.product_ids("closet", user["id"])) if user else set()
    outfit = recommend.suggest_outfit(product_id, owned_ids=owned)
    if outfit is None:
        raise HTTPException(404, "Product not found")
    cards = {c.product_id: c for c in tools.product_cards([x["product"].product_id for x in outfit["pieces"]], limit=10)}
    return {"pieces": [{"product": cards[x["product"].product_id], "role": x["role"], "tip": x["tip"],
                        "why_it_matches": x["why_it_matches"], "already_owned": x["already_owned"]}
                       for x in outfit["pieces"] if x["product"].product_id in cards]}
