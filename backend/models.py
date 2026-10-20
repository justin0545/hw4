"""Pydantic types for the Campus Customs shop agent.

Three groups:
  - API types:      what the website sends to /api/chat and gets back
  - Agent output:   what the model must return at the end of every run
  - Tool results:   what the tools hand back to the model

The model never types out prices, stock or image paths. It returns product
IDs (chat cards) and a search_id (page results) in ShopReply, and main.py builds
every ProductCard from the database.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MAX_MESSAGE_CHARS = 2000
MAX_HISTORY_MESSAGES = 20
MAX_CARDS = 6
MAX_PAGE_RESULTS = 48  # cards a chat search can put on the page


# ---- API: website <-> FastAPI ----------------------------------------------

class ChatTurn(BaseModel):
    """One earlier message in the conversation, as the chat widget holds it."""

    role: Literal["user", "assistant"]
    content: str = Field(max_length=MAX_MESSAGE_CHARS * 4)
    product_ids: list[str] = Field(
        default_factory=list, max_length=MAX_CARDS,
        description="Assistant turns only: the products shown as cards under that reply.",
    )


class PageContext(BaseModel):
    """Where the shopper is on the site when they send a message (Problem 8).

    Only identifiers come from the browser. The server looks the product up in
    the database itself, so nothing the browser sends is pasted into the prompt
    as free text.
    """

    path: str = Field(default="/", max_length=200, pattern=r"^/[A-Za-z0-9/_\-]*$",
                      description="URL path, e.g. /products/basic-hoodie-big-yale.")
    product_id: str | None = Field(default=None, max_length=120, pattern=r"^[a-z0-9\-]+$",
                                   description="Set when the shopper is on a single-item page.")
    showing_chat_results: bool = Field(default=False, description="True if chat search results fill the Products page.")


class ChatRequest(BaseModel):
    """POST /api/chat body."""

    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    history: list[ChatTurn] = Field(
        default_factory=list,
        description="Earlier turns, oldest first. Used for guests only; logged-in shoppers' history comes from the database.",
    )
    page: PageContext | None = None


class ProductCard(BaseModel):
    """A product card for the website (chat panel or page). Built from the database, not by the model."""

    product_id: str
    name: str
    garment_type: str
    description: str = Field(description="Catalogue description; the page shows it as the card's short info.")
    price: float
    image_url: str
    colors: list[str]
    sizes_in_stock: list[str]
    total_stock: int


class PageResults(BaseModel):
    """Search results the website renders as product cards on the page (Problem 7).

    Every product here is a match from a search_products call the agent made this
    turn, in the order the search ranked them. The page links each card to
    /products/{product_id}, the same detail view as the Products page.
    """

    title: str = Field(description="Heading for the results, e.g. 'Hoodies' or 'Navy items in XL'.")
    query: str = Field(description="The words the agent searched for.")
    filters: dict[str, str | float] = Field(default_factory=dict, description="Filters the search applied.")
    total_matches: int
    products: list[ProductCard]


class ChatReply(BaseModel):
    """POST /api/chat response."""

    reply: str
    products: list[ProductCard] = Field(default_factory=list, description="Up to 6 cards shown in the chat panel.")
    page_results: PageResults | None = Field(
        default=None, description="Present when the agent chose to show a search on the page.",
    )


class HistoryMessage(BaseModel):
    """One saved message, as GET /api/chat/history returns it (Problem 8)."""

    role: Literal["user", "assistant"]
    content: str
    created_at: str
    products: list[ProductCard] = Field(default_factory=list)
    page_results: PageResults | None = None


class ChatHistory(BaseModel):
    """GET /api/chat/history response. Empty for guests."""

    logged_in: bool
    messages: list[HistoryMessage] = Field(default_factory=list)


class ListItem(BaseModel):
    """One saved item in My Closet or the Wish List (Problem 9)."""

    id: int
    size: str | None = None
    added_at: str
    product: ProductCard = Field(description="Fresh from the catalogue: current price and stock.")
    size_status: Literal["in stock", "sold out"] | None = Field(
        default=None, description="Stock of the saved size right now, if a size was saved.")


class ListAddRequest(BaseModel):
    product_id: str = Field(max_length=120, pattern=r"^[a-z0-9\-]+$")
    size: str | None = Field(default=None, max_length=20)


class Recommendation(BaseModel):
    """One personal recommendation, with the reason in plain words (Problem 9)."""

    product: ProductCard
    reason: str = Field(description="Why it's recommended, e.g. 'Similar to your Basic Hoodie Big Yale (in your closet)'.")
    score: float


class Recommendations(BaseModel):
    """GET /api/recommendations response."""

    personalized: bool = Field(description="False for guests or shoppers with no history yet (popular picks instead).")
    based_on: dict[str, int] = Field(default_factory=dict,
                                     description="How many closet, wish-list and chat products shaped the picks.")
    items: list[Recommendation] = Field(default_factory=list)


# ---- Agent output ------------------------------------------------------------

class ShopReply(BaseModel):
    """What the agent returns at the end of every turn."""

    message: str = Field(
        description="Your reply to the shopper, in the Campus Customs voice. Plain text, no markdown."
    )
    product_ids: list[str] = Field(
        default_factory=list,
        max_length=MAX_CARDS,
        description="product_id of each item you mention or recommend, best first (at most 6). "
        "Only IDs returned by a tool in this conversation. Empty if no products are relevant.",
    )
    page_search_id: str | None = Field(
        default=None,
        description="When the shopper is browsing a kind of item (e.g. 'what hoodies do you have?'), the "
        "search_id of the search_products call whose matches should fill the web page. Null for questions "
        "about one specific product, stock or price checks, and small talk.",
    )
    page_title: str | None = Field(
        default=None,
        description="Short heading for the page results, e.g. 'Hoodies' or 'Navy crewnecks'. Required with page_search_id.",
    )


# ---- Tool results --------------------------------------------------------------
#
# What the tools hand back to the model. Field choices (why each field is here,
# and why some database columns are left out) are explained in
# output/harness.md section 6. In short:
#   - names say their unit or meaning (price_usd, quantity_in_stock) so the model
#     can't misread them
#   - stock status is computed in code (StockStatus), so "sold out" is never a
#     judgment call by the model
#   - internal columns (search_tags, image_file_path) stay out of tool results

LOW_STOCK_THRESHOLD = 5  # same threshold the product page uses for "Only N left"

StockStatus = Literal["in stock", "low stock", "sold out", "size not offered"]


class SizeStock(BaseModel):
    """Stock for one size of one product."""

    size: str = Field(description="XS, S, M, L, XL or XXL.")
    quantity_in_stock: int = Field(description="Units on hand right now, from the inventory table.")
    status: StockStatus = Field(description=f"'low stock' means {LOW_STOCK_THRESHOLD} or fewer left.")


class ProductSummary(BaseModel):
    """One search hit: enough to recommend and compare, not the full record."""

    product_id: str = Field(description="Use this to call get_product or check_stock, and in product_ids.")
    name: str
    garment_type: str
    price_usd: float
    colors: list[str]
    sizes_in_stock: list[str] = Field(description="Sizes with at least one unit, smallest first.")
    sold_out_sizes: list[str] = Field(description="Sizes with zero units.")
    total_in_stock: int = Field(description="Units on hand across all sizes.")


class ProductDetail(BaseModel):
    """Everything a shopper might ask about one product: description, price, stock by size."""

    product_id: str
    name: str
    garment_type: str
    description: str = Field(description="Catalogue description. Quote or paraphrase it; don't add details.")
    price_usd: float
    colors: list[str]
    stock_by_size: list[SizeStock] = Field(description="Every size, smallest first, including sold-out ones.")
    sizes_in_stock: list[str]
    sold_out_sizes: list[str]
    total_in_stock: int
    is_sold_out: bool = Field(description="True only if every size is at zero.")


class SearchResult(BaseModel):
    search_id: str = Field(description="Pass as page_search_id to show ALL of this search's matches on the web page.")
    query: str
    filters: dict[str, str | float] = Field(default_factory=dict, description="Filters that were applied.")
    total_matches: int
    products: list[ProductSummary]
    note: str = ""


class OutfitPiece(BaseModel):
    """One piece that goes with the base item (suggest_outfit tool, Problem 10)."""

    product: ProductSummary
    role: str = Field(description="'wear over' or 'wear under' the base piece.")
    tip: str = Field(description="How to wear them together. Rephrase in your own excited words.")
    why_it_matches: str = Field(description="e.g. 'matching vintage theme' or 'colors that go together'.")
    already_owned: bool = Field(description="True if it's in the shopper's closet: suggest wearing what they have.")


class OutfitResult(BaseModel):
    base: ProductSummary
    occasion: str = ""
    pieces: list[OutfitPiece]
    search_id: str = Field(description="Pass as page_search_id to show the base piece + these pieces on the page.")


class CustomerAccount(BaseModel):
    """The logged-in shopper's own account details (get_my_account tool, Problem 8)."""

    first_name: str
    last_name: str
    email: str = Field(description="Only ever share with this shopper themselves.")
    member_since: str = Field(description="Date the account was created, YYYY-MM-DD.")
    days_as_member: int = Field(description="Whole days since member_since, computed today. Use this; don't do date math.")
    saved_chat_messages: int = Field(description="Messages saved in their chat history, including this conversation.")


class StockCheck(BaseModel):
    """Answer to "is size X of product Y in stock, and how many?"."""

    product_id: str
    name: str
    price_usd: float
    size: str = Field(description="The size checked, normalized to XS/S/M/L/XL/XXL.")
    quantity_in_stock: int
    status: StockStatus
    other_sizes_in_stock: list[str] = Field(description="Alternatives to offer if this size is sold out or low.")
    note: str = Field(default="", description="Instruction for how to phrase the answer, when it matters.")


# ---- Audit trail (Problem 12) ----------------------------------------------------
#
# One entry per agent-loop step, appended to output/audit_trail.json (never wiped).
# Short by design: clipped args and result summaries, a redacted message preview,
# and the shopper as "user:<id>" or "guest" (no names or emails in the log).

class ToolCallRecord(BaseModel):
    tool_name: str
    args: dict = Field(default_factory=dict, description="Arguments, long values clipped.")


class ToolResultRecord(BaseModel):
    tool_name: str
    outcome: Literal["ok", "retry", "error"] = Field(description="retry = the tool or validator sent the model back to fix something.")
    summary: str = Field(description="One-line summary of what the tool returned, clipped.")


class AuditEntry(BaseModel):
    """One step of the agent loop. A step = one model response, the tools it called and what they returned."""

    timestamp: str = Field(description="UTC ISO-8601 time the step finished.")
    run_id: str = Field(description="Groups the steps of one chat message; many runs share the file.")
    step: int = Field(ge=0, description="1 = first model response in this run. 0 = an event with no model call (guardrail, block).")
    shopper: str = Field(description="'user:<id>' or 'guest'.")
    page: str = Field(default="", description="Where they were: path, plus product_id on a product page.")
    message_preview: str = Field(default="", description="The shopper's message, sensitive data redacted, clipped to 160 chars.")
    model_name: str = ""
    model_text: str = Field(default="", description="Plain text the model returned at this step, clipped.")
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    tool_results: list[ToolResultRecord] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str | None = Field(default=None, description="Set on the last step only: why the run ended.")
