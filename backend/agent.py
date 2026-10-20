"""Campus Customs shop agent: entry point and wiring (PydanticAI).

    prompts/prompt.md   system prompt (voice, how to answer, safety basics)
    tools.py            tool logic + model wiring (Portkey gateway)
    models.py           types: API request/response, agent output, tool results

main.py calls run_chat() for every POST /api/chat. One run = one shopper
message: the model may call tools a few times, then must return a ShopReply.

Tools the agent can call:

    search_products   find items by keywords and filters (type, color, price, size)
    get_product       full details and stock by size for one item
    check_stock       is a given size of an item in stock?
    get_my_account    the logged-in shopper's own name, email, member-since date
    recommend_for_me  personal picks from closet, wish list and chat history (Problem 9)
    get_my_lists      what's in their closet and on their wish list (Problem 9)
    add_to_wish_list  save an item to their wish list (Problem 9)
    suggest_outfit    pieces that go with an item: layering + colors + theme (Problem 10)

Context the agent gets every message (Problem 8), via ChatDeps + @agent.instructions:

    customer          who is chatting (name, email), from the session cookie, or None for guests
    page              where they are on the site; on a product page, which product
                      ("do you have this in pink?" -> this = that product)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

import uuid

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.usage import UsageLimits

import audit
import chat_store
import guardrails
import recommend
import shopper_lists
import tools
from models import (
    MAX_HISTORY_MESSAGES,
    AuditEntry,
    ToolCallRecord,
    ToolResultRecord,
    ListItem,
    OutfitPiece,
    OutfitResult,
    Recommendations,
    ChatTurn,
    CustomerAccount,
    PageContext,
    ProductDetail,
    SearchResult,
    ShopReply,
    StockCheck,
)

HERE = Path(__file__).parent
PROMPT_PATH = HERE / "prompts" / "prompt.md"

# Loop limits per shopper message. A normal turn is 1-3 model requests (search,
# maybe a stock check, then the reply); the caps stop a confused model from looping.
# Tool calls made in parallel in one step each count toward MAX_TOOL_CALLS.
MAX_AGENT_STEPS = 6
MAX_TOOL_CALLS = 12
LIMITS = UsageLimits(request_limit=MAX_AGENT_STEPS, tool_calls_limit=MAX_TOOL_CALLS)


@dataclass
class Customer:
    """The logged-in shopper, from the session cookie (never from anything typed in chat)."""

    id: int
    first_name: str
    last_name: str
    email: str
    member_since: str  # users.created_at, YYYY-MM-DD
    joined_at: str = ""  # users.created_at in full (UTC), for day counts

    @classmethod
    def from_user(cls, user: dict) -> Customer:
        return cls(id=user["id"], first_name=user["first_name"] or "", last_name=user["last_name"] or "",
                   email=user["email"], member_since=(user.get("member_since") or "")[:10],
                   joined_at=user.get("member_since") or "")


@dataclass
class PageView:
    """Where the shopper is on the site, rebuilt on the server from the browser's PageContext."""

    path: str
    page_type: str                   # home, products, product, about, login, create-account, other
    product: ProductDetail | None    # set on a single-item page, looked up in the database
    showing_chat_results: bool = False


PAGE_TYPES = {"/": "home", "/products": "products", "/about": "about", "/login": "login",
              "/create-account": "create-account"}


def build_page_view(page: PageContext | None) -> PageView | None:
    """Trust only identifiers from the browser: the product is fetched from the database by ID."""
    if page is None:
        return None
    product = tools.get_product(page.product_id) if page.product_id else None
    page_type = "product" if product else PAGE_TYPES.get(page.path.rstrip("/") or "/", "other")
    return PageView(path=page.path, page_type=page_type, product=product,
                    showing_chat_results=page.showing_chat_results and page_type == "products")


@dataclass
class ChatDeps:
    """Per-run state shared by the tools and instructions."""

    customer: Customer | None = None   # None = guest
    page: PageView | None = None
    safety_notes: list[str] = field(default_factory=list)  # e.g. "the shopper typed a card number (redacted)"
    # Product IDs the tools returned this turn; the reply may only show these
    # (or ones already shown earlier in the conversation).
    seen_product_ids: set[str] = field(default_factory=set)
    tool_log: list[str] = field(default_factory=list)
    # Every search_products call this turn, by search_id, with ALL its matches
    # (the model only sees the best 8). The page results come from here.
    searches: dict[str, PageSearch] = field(default_factory=dict)


@dataclass
class PageSearch:
    """One search the agent ran, kept so its full results can go to the web page."""

    query: str
    filters: dict
    product_ids: list[str]


@dataclass
class ChatOutcome:
    """What run_chat hands back to main.py."""

    reply: ShopReply
    tool_log: list[str]
    page_search: PageSearch | None  # the search the agent chose to show on the page


agent = Agent(
    deps_type=ChatDeps,
    output_type=ShopReply,
    retries=2,
)


@agent.instructions
def system_prompt() -> str:
    """prompts/prompt.md, re-read on every message so edits apply without restarting
    the server (uvicorn --reload only watches .py files)."""
    return PROMPT_PATH.read_text(encoding="utf-8")


@agent.instructions
def shopper_context(ctx: RunContext[ChatDeps]) -> str:
    """Added to the system prompt each run: who is chatting."""
    c = ctx.deps.customer
    if c is None:
        return ("## Who is chatting\nA guest (not logged in). This conversation isn't saved after they leave. "
                "If they ask you to remember something for next time, suggest creating an account.")
    return (
        "## Who is chatting\n"
        f"A logged-in customer: {c.first_name} {c.last_name} ({c.email}), member since {c.member_since}. "
        "Earlier messages in this conversation are their saved chat history, which may be from past visits. "
        "Call get_my_account if they ask about their account."
    )


@agent.instructions
def safety_context(ctx: RunContext[ChatDeps]) -> str:
    """Notes from the code guardrails for this message (guardrails.py), e.g. that something was redacted."""
    return "\n".join(ctx.deps.safety_notes)


@agent.instructions
def page_context(ctx: RunContext[ChatDeps]) -> str:
    """Added to the system prompt each run: where the shopper is on the site."""
    page = ctx.deps.page
    if page is None:
        return ""
    if page.product is not None:
        p = page.product
        return (
            "## Where the shopper is\n"
            f"They're on the product page for {p.name} (product_id: {p.product_id}, {p.garment_type}, "
            f"${p.price_usd:g}, colors: {', '.join(p.colors)}). "
            'If they say "this", "it" or "this one", or ask about a color or size without naming an item, '
            "they mean this product. Use get_product or check_stock for its stock before answering."
        )
    where = {"home": "the home page", "products": "the Products page", "about": "the About Us page",
             "login": "the Log in page", "create-account": "the Create Account page"}.get(page.page_type, page.path)
    extra = " It's showing the search results you last put on the page." if page.showing_chat_results else ""
    return f"## Where the shopper is\nThey're on {where}.{extra}"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@agent.tool
def search_products(
    ctx: RunContext[ChatDeps],
    query: str = "",
    garment_type: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    size: str | None = None,
) -> SearchResult:
    """Find products. Returns up to 8 matches, each with price_usd, colors, sizes_in_stock and sold_out_sizes.

    Use this first whenever the shopper describes what they want or names a product
    (to get its product_id). Every word in `query` must match the product somewhere,
    so keep queries to a few key words, e.g. "bulldog hoodie", "hockey" or "Basic Hoodie Big Yale".

    Args:
        query: Key words from the shopper. May be empty when using filters.
        garment_type: Optional filter, e.g. "hoodie", "crewneck", "t-shirt", "quarter-zip", "jacket".
        color: Optional color filter, e.g. "navy", "gray", "white".
        max_price: Optional highest price in US dollars.
        size: Optional size that must be in stock, e.g. "M" or "medium". Only items with stock in that size come back.
    """
    ctx.deps.tool_log.append("search_products")
    search_id = f"search_{len(ctx.deps.searches) + 1}"
    result, all_ids = tools.search_products(query, garment_type, color, max_price, size, search_id=search_id)
    ctx.deps.searches[search_id] = PageSearch(query=query, filters=result.filters, product_ids=all_ids)
    ctx.deps.seen_product_ids.update(p.product_id for p in result.products)
    return result


def _unknown_product(product_id: str) -> ModelRetry:
    """Retry message for a bad product_id, with the closest real products to pick from."""
    ideas = tools.suggest_products(product_id)
    hint = "; ".join(f"{p.product_id} ({p.name})" for p in ideas)
    return ModelRetry(
        f"No product has product_id {product_id!r}. "
        + (f"Closest matches: {hint}. " if hint else "")
        + "Use an exact product_id from search_products."
    )


@agent.tool
def get_product(ctx: RunContext[ChatDeps], product_id: str) -> ProductDetail:
    """Look up one product's description, price and stock for every size, straight from the database.

    Use for "tell me about…", "how much is…", "what sizes does … come in", or
    "how many are left" when no single size is named.

    Args:
        product_id: Exact product_id from a search result, e.g. "basic-hoodie-big-yale".
    """
    ctx.deps.tool_log.append("get_product")
    detail = tools.get_product(product_id)
    if detail is None:
        raise _unknown_product(product_id)
    ctx.deps.seen_product_ids.add(product_id)
    return detail


@agent.tool
def check_stock(ctx: RunContext[ChatDeps], product_id: str, size: str) -> StockCheck:
    """Check one size of one product: quantity_in_stock, status (in stock / low stock / sold out) and other sizes in stock.

    Use when the shopper names a size for a specific product ("is the Basic Hoodie in medium?",
    "how many smalls are left?"). Call it once per size asked about.

    Args:
        product_id: Exact product_id from a search result.
        size: The size asked about, e.g. "M", "medium", "XL", "2XL".
    """
    ctx.deps.tool_log.append("check_stock")
    try:
        result = tools.check_stock(product_id, size)
    except ValueError:
        raise ModelRetry(f"{size!r} isn't a size we stock. Sizes are {', '.join(tools.SIZE_ORDER)}.")
    if result is None:
        raise _unknown_product(product_id)
    ctx.deps.seen_product_ids.add(product_id)
    return result


@agent.tool
def get_my_account(ctx: RunContext[ChatDeps]) -> CustomerAccount | str:
    """The logged-in shopper's own account: first and last name, email, member-since date, saved messages.

    Use when they ask "what's my email?", "do you remember me?", or about their account.
    Only ever returns the shopper's own details.
    """
    ctx.deps.tool_log.append("get_my_account")
    c = ctx.deps.customer
    if c is None:
        return "The shopper is a guest (not logged in), so there's no account. They can log in or create one."
    try:  # users.created_at is UTC; compare full timestamps so the server's time zone doesn't matter
        joined = datetime.fromisoformat(c.joined_at).replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - joined).days
    except ValueError:
        days = 0
    return CustomerAccount(first_name=c.first_name, last_name=c.last_name, email=c.email,
                           member_since=c.member_since, days_as_member=days,
                           saved_chat_messages=chat_store.count_messages(c.id))


class RecommendationResult(Recommendations):
    """recommend_for_me result. search_id works like a search's: pass it as page_search_id."""

    search_id: str = ""


@agent.tool
def recommend_for_me(ctx: RunContext[ChatDeps], limit: int = 6) -> RecommendationResult:
    """Personal recommendations for this shopper, each with a reason, from what's in their closet
    (what they own), on their wish list, and what they've looked at in chat. Guests or new
    shoppers get staff picks (personalized = false). Only in-stock items they don't already have.

    Use for "what would you recommend for me?", "what else would I like?", "suggest something".
    To show them on the page, pass the returned search_id as page_search_id.

    Args:
        limit: How many picks, 1-12.
    """
    ctx.deps.tool_log.append("recommend_for_me")
    c = ctx.deps.customer
    recs = recommend.recommend(c.id if c else None, limit=max(1, min(limit, 12)))
    search_id = f"search_{len(ctx.deps.searches) + 1}"
    ids = [r.product.product_id for r in recs.items]
    ctx.deps.searches[search_id] = PageSearch(query="recommended for you", filters={}, product_ids=ids)
    ctx.deps.seen_product_ids.update(ids)
    return RecommendationResult(**recs.model_dump(), search_id=search_id)


@agent.tool
def get_my_lists(ctx: RunContext[ChatDeps]) -> dict[str, list[ListItem]] | str:
    """The shopper's My Closet (items they own) and Wish List (items they want), with current price and stock.

    Use for "what's on my wish list?", "is anything on my wish list back in stock?", "what do I own?".
    """
    ctx.deps.tool_log.append("get_my_lists")
    c = ctx.deps.customer
    if c is None:
        return "The shopper is a guest. My Closet and Wish List need an account; suggest logging in."
    lists = {"closet": shopper_lists.list_items("closet", c.id), "wishlist": shopper_lists.list_items("wishlist", c.id)}
    ctx.deps.seen_product_ids.update(i.product.product_id for items in lists.values() for i in items)
    return lists


@agent.tool
def add_to_wish_list(ctx: RunContext[ChatDeps], product_id: str, size: str | None = None) -> ListItem | str:
    """Save a product (optionally in a size) to the shopper's Wish List. Only when they ask you to.

    Args:
        product_id: Exact product_id from a search, or the product they're viewing.
        size: Optional size they want, e.g. "M".
    """
    ctx.deps.tool_log.append("add_to_wish_list")
    c = ctx.deps.customer
    if c is None:
        return "The shopper is a guest, so there's no wish list. Suggest logging in or creating an account."
    try:
        item = shopper_lists.add_item("wishlist", c.id, product_id, size)
    except KeyError:
        raise _unknown_product(product_id)
    except ValueError:
        raise ModelRetry(f"{size!r} isn't a size we stock. Sizes are {', '.join(tools.SIZE_ORDER)}.")
    ctx.deps.seen_product_ids.add(product_id)
    return item


@agent.tool
def suggest_outfit(ctx: RunContext[ChatDeps], product_id: str, occasion: str = "") -> OutfitResult:
    """Build an outfit around one product: in-stock pieces to wear over or under it, chosen by layering
    rules, matching colors and matching themes (same college, sport, bulldog...). Pieces the shopper
    already owns (their closet) come first.

    Use whenever a shopper picks or is looking at an item, or asks "what goes with this?",
    "how should I wear it?", "complete the look". To show the outfit on the page, pass search_id
    as page_search_id.

    Args:
        product_id: The base item's exact product_id (on a product page, that product).
        occasion: What they told you, e.g. "game day at the Yale Bowl", "class", "gift". Optional.
    """
    ctx.deps.tool_log.append("suggest_outfit")
    owned = set(shopper_lists.product_ids("closet", ctx.deps.customer.id)) if ctx.deps.customer else set()
    outfit = recommend.suggest_outfit(product_id, owned_ids=owned)
    if outfit is None:
        raise _unknown_product(product_id)
    ids = [product_id] + [x["product"].product_id for x in outfit["pieces"]]
    search_id = f"search_{len(ctx.deps.searches) + 1}"
    ctx.deps.searches[search_id] = PageSearch(query=f"outfit with {outfit['base'].name}", filters={}, product_ids=ids)
    ctx.deps.seen_product_ids.update(ids)
    pieces = [OutfitPiece(**{k: v for k, v in x.items() if k != "score"}) for x in outfit["pieces"]]
    return OutfitResult(base=outfit["base"], occasion=occasion, pieces=pieces, search_id=search_id)


@agent.output_validator
def only_real_products(ctx: RunContext[ChatDeps], reply: ShopReply) -> ShopReply:
    """Product cards must point at real products the tools actually returned."""
    unknown = [pid for pid in reply.product_ids if pid not in ctx.deps.seen_product_ids]
    if unknown:
        raise ModelRetry(
            f"These product_ids weren't returned by a tool: {unknown}. "
            "Look them up with search_products or get_product first, or remove them."
        )
    if reply.page_search_id is not None:
        search = ctx.deps.searches.get(reply.page_search_id)
        if search is None:
            raise ModelRetry(
                f"page_search_id {reply.page_search_id!r} isn't a search from this turn. "
                f"Use one of {list(ctx.deps.searches) or 'none: call search_products first'}, or set it to null."
            )
        if not search.product_ids:
            raise ModelRetry(f"{reply.page_search_id} found nothing, so there's nothing to show on the page. "
                             "Set page_search_id to null, or use a search that found matches.")
        if not (reply.page_title or "").strip():
            raise ModelRetry("Give a short page_title for the page results, e.g. 'Hoodies'.")
    return reply


# ---------------------------------------------------------------------------
# Entry point used by main.py
# ---------------------------------------------------------------------------

_model = None
model_name: str | None = None


def get_model():
    """Build the model once, on first use, so the server can start without a key."""
    global _model, model_name
    if _model is None:
        _model, model_name = tools.build_model()
    return _model


def _to_message_history(history: list[ChatTurn]) -> list[ModelMessage]:
    """The widget's earlier turns as PydanticAI messages (most recent MAX_HISTORY_MESSAGES)."""
    messages: list[ModelMessage] = []
    for turn in history[-MAX_HISTORY_MESSAGES:]:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            text = turn.content
            if turn.product_ids:  # so "is the first one in M?" can be resolved
                text += f"\n[Product cards shown, in order: {', '.join(turn.product_ids)}]"
            messages.append(ModelResponse(parts=[TextPart(content=text)]))
    return messages


def _results_from_request(request: ModelRequest) -> list[ToolResultRecord]:
    """Tool results reach the model in the next request: returns, or retry prompts (tool/validator said fix it)."""
    out = []
    for part in request.parts:
        if isinstance(part, ToolReturnPart):
            out.append(ToolResultRecord(tool_name=part.tool_name, outcome="ok", summary=audit.summarize(part.tool_name, part.content)))
        elif isinstance(part, RetryPromptPart):
            msg = part.content if isinstance(part.content, str) else str(part.content)
            out.append(ToolResultRecord(tool_name=part.tool_name or "output_validator", outcome="retry", summary=audit.clip(msg)))
    return out


async def run_chat(
    message: str,
    history: list[ChatTurn],
    customer: Customer | None = None,
    page: PageView | None = None,
    safety_notes: list[str] | None = None,
) -> ChatOutcome:
    """Run the agent on one shopper message, writing every loop step to the audit trail.

    message: already scrubbed by guardrails.scrub_input (main.py).
    history: saved history from the database for logged-in shoppers, or what the
    browser sent for guests (main.py decides which).
    """
    # History comes from the browser, so only real catalogue IDs carry over.
    known = tools.known_product_ids()
    history = [t.model_copy(update={"product_ids": [p for p in t.product_ids if p in known]}) for t in history]
    shown = {pid for t in history for pid in t.product_ids}
    if page and page.product:
        shown.add(page.product.product_id)  # the item they're looking at can be shown as a card
    deps = ChatDeps(customer=customer, page=page, seen_product_ids=shown, safety_notes=list(safety_notes or []))

    # Audit: one entry per step = one model response + the tools it called + what they returned.
    base = {
        "run_id": uuid.uuid4().hex[:12],
        "shopper": f"user:{customer.id}" if customer else "guest",
        "page": (page.path + (f" ({page.product.product_id})" if page.product else "")) if page else "",
        "message_preview": audit.clip(message, 160),
    }
    entries: list[AuditEntry] = []
    pending: AuditEntry | None = None
    step, finish = 0, None
    try:
        async with agent.iter(
            message,
            model=get_model(),
            deps=deps,
            message_history=_to_message_history(history),
            usage_limits=LIMITS,
            model_settings={"max_tokens": guardrails.MAX_REPLY_TOKENS},
        ) as run:
            async for node in run:
                if Agent.is_call_tools_node(node):
                    step += 1
                    resp = node.model_response
                    finish = resp.finish_reason
                    pending = AuditEntry(
                        timestamp=audit.now(), step=step, model_name=resp.model_name or "",
                        model_text=audit.clip(" ".join(p.content for p in resp.parts if isinstance(p, TextPart))),
                        tool_calls=[ToolCallRecord(tool_name=p.tool_name, args=audit.short_args(p.args_as_dict()))
                                    for p in resp.parts if isinstance(p, ToolCallPart)],
                        input_tokens=resp.usage.input_tokens or 0, output_tokens=resp.usage.output_tokens or 0, **base,
                    )
                elif Agent.is_model_request_node(node) and pending is not None:
                    pending.tool_results = _results_from_request(node.request)
                    pending.timestamp = audit.now()
                    entries.append(pending)
                    pending = None
                elif Agent.is_end_node(node) and pending is not None:
                    out = node.data.output
                    pending.tool_results = [ToolResultRecord(
                        tool_name="final_result", outcome="ok",
                        summary=audit.clip(f"reply {len(out.message)} chars; cards {out.product_ids}; page_search {out.page_search_id}"))]
                    pending.stop_reason = f"final_result: ShopReply returned (model finish_reason={finish})"
                    pending.timestamp = audit.now()
                    entries.append(pending)
                    pending = None
            reply = run.result.output
    except Exception as exc:
        entry = pending or AuditEntry(timestamp=audit.now(), step=step, **base)
        entry.timestamp = audit.now()
        if isinstance(exc, ModelHTTPError) and "content_filter" in str(exc.body):
            entry.stop_reason = "blocked: model provider's content filter rejected the request"
        else:
            entry.stop_reason = f"error: {type(exc).__name__}: {audit.clip(exc, 200)}"
        entries.append(entry)
        raise
    finally:
        audit.append(entries)

    chosen = deps.searches.get(reply.page_search_id) if reply.page_search_id else None
    return ChatOutcome(reply=reply, tool_log=deps.tool_log, page_search=chosen)
