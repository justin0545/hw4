"""Tools and helpers for the Campus Customs shop agent.

agent.py wires these into the PydanticAI agent; this file holds the logic.

Tools the agent can call (all read-only, all against data/campus_customs.db):

    search_products   keyword + filter search over the catalogue, with stock
    get_product       full record for one product, stock by size
    check_stock       is one size of one product in stock?

Also here: loading products for the website API (main.py uses the same
function, so the chat and the product pages always agree), building product
cards, and building the model (Portkey gateway, as in Homework 3).
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path

import images
from db import connect
from models import (
    LOW_STOCK_THRESHOLD,
    MAX_CARDS,
    ProductCard,
    ProductDetail,
    ProductSummary,
    SearchResult,
    SizeStock,
    StockCheck,
    StockStatus,
)

HERE = Path(__file__).parent
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
MAX_SEARCH_RESULTS = 8

# Words shoppers use for sizes -> the codes in the inventory table.
SIZE_ALIASES = {
    "xs": "XS", "extra small": "XS", "x-small": "XS", "xsmall": "XS",
    "s": "S", "small": "S", "sm": "S",
    "m": "M", "medium": "M", "med": "M",
    "l": "L", "large": "L", "lg": "L",
    "xl": "XL", "extra large": "XL", "x-large": "XL", "xlarge": "XL",
    "xxl": "XXL", "2xl": "XXL", "xx-large": "XXL", "xxlarge": "XXL", "double xl": "XXL",
    "extra extra large": "XXL",
}


def normalize_size(size: str) -> str | None:
    """'medium' -> 'M', '2XL' -> 'XXL'. None if it isn't a size we stock."""
    return SIZE_ALIASES.get(re.sub(r"\s+", " ", size.strip().lower()))

PORTKEY_BASE_URL_DEFAULT = "https://api.portkey.ai/v1"
MODEL_DEFAULT = "gpt-5.6-luna-2026-07-09"  # same as Homework 3; the course key routes here regardless


# ---------------------------------------------------------------------------
# Products from the database (shared by the website API and the agent)
# ---------------------------------------------------------------------------

def _size_key(size: str) -> int:
    return SIZE_ORDER.index(size) if size in SIZE_ORDER else 99


def _product_from_row(row: sqlite3.Row, inventory: list[dict]) -> dict:
    p = dict(row)
    p["colors"] = json.loads(p["colors"])
    p["search_tags"] = json.loads(p["search_tags"])
    # Compressed versions (images.py): small WebP for cards, larger WebP for the product page.
    p["image_url"] = images.variant_url(p["image_file_path"], "card")
    p["image_url_large"] = images.variant_url(p["image_file_path"], "large")
    p["image_url_original"] = f"/media/{p['image_file_path']}"
    p["inventory"] = sorted(inventory, key=lambda i: _size_key(i["size"]))
    p["total_stock"] = sum(i["quantity"] for i in inventory)
    return p


def load_products(product_id: str | None = None) -> list[dict]:
    """Catalogue rows joined with inventory. One product if product_id is given."""
    where, args = ("where product_id = ?", (product_id,)) if product_id else ("", ())
    with connect() as con:
        rows = con.execute(f"select * from catalogue {where} order by name", args).fetchall()
        inv: dict[str, list[dict]] = {}
        for r in con.execute(f"select product_id, size, quantity from inventory {where}", args):
            inv.setdefault(r["product_id"], []).append({"size": r["size"], "quantity": r["quantity"]})
    return [_product_from_row(r, inv.get(r["product_id"], [])) for r in rows]


def _sizes_in_stock(p: dict) -> list[str]:
    return [i["size"] for i in p["inventory"] if i["quantity"] > 0]


def _sold_out_sizes(p: dict) -> list[str]:
    return [i["size"] for i in p["inventory"] if i["quantity"] == 0]


def stock_status(quantity: int | None) -> StockStatus:
    """Decided in code, not by the model: 0 is sold out, 1-5 is low, None means no inventory row."""
    if quantity is None:
        return "size not offered"
    if quantity == 0:
        return "sold out"
    return "low stock" if quantity <= LOW_STOCK_THRESHOLD else "in stock"


def _summary(p: dict) -> ProductSummary:
    return ProductSummary(
        product_id=p["product_id"], name=p["name"], garment_type=p["garment_type"], price_usd=p["price"],
        colors=p["colors"], sizes_in_stock=_sizes_in_stock(p), sold_out_sizes=_sold_out_sizes(p),
        total_in_stock=p["total_stock"],
    )


def product_cards(product_ids: list[str], limit: int = MAX_CARDS) -> list[ProductCard]:
    """Cards for the website (chat panel or page), in the given order. Unknown IDs are dropped."""
    by_id = {p["product_id"]: p for p in load_products()}
    cards = []
    for pid in dict.fromkeys(product_ids):  # de-duplicate, keep order
        if p := by_id.get(pid):
            cards.append(ProductCard(
                product_id=pid, name=p["name"], garment_type=p["garment_type"], description=p["description"],
                price=p["price"], image_url=p["image_url"], colors=p["colors"],
                sizes_in_stock=_sizes_in_stock(p), total_stock=p["total_stock"],
            ))
    return cards[:limit]


def known_product_ids() -> set[str]:
    with connect() as con:
        return {r[0] for r in con.execute("select product_id from catalogue")}


# ---------------------------------------------------------------------------
# Tool logic
# ---------------------------------------------------------------------------

# Shopper words -> words the catalogue uses.
SYNONYMS = {
    "hoodie": ["hoodie", "hood", "hooded"],
    "hoody": ["hoodie", "hood", "hooded"],
    "sweatshirt": ["sweatshirt", "crewneck", "hoodie", "hooded"],
    "crew": ["crewneck", "crew"],
    "tee": ["t-shirt", "tee"],
    "tshirt": ["t-shirt"],
    "shirt": ["t-shirt", "shirt"],
    "quarter": ["1/4", "quarter"],
    "zip": ["zip"],
    "grey": ["gray", "grey", "heather"],
    "gray": ["gray", "grey", "heather"],
    "blue": ["blue", "navy"],
    "dog": ["bulldog"],
    "jacket": ["jacket", "fleece", "bomber"],
    "sweater": ["sweater", "fleece", "crewneck"],
}
STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "in", "of", "to", "on", "do", "you", "have", "any",
    "i", "me", "my", "is", "are", "some", "show", "want", "need", "looking", "something", "yale",
    "please", "what", "items", "item", "stuff", "gear", "apparel",
}


def _terms(query: str) -> list[list[str]]:
    """Each shopper word becomes a group of alternatives; a product matches the word if any alternative hits."""
    groups = []
    for word in re.findall(r"[a-z0-9/\-]+", query.lower()):
        if word in STOPWORDS:
            continue
        if word.endswith("s") and len(word) > 3 and word not in {"dress", "glass"}:
            word = word[:-1]  # hoodies -> hoodie, tees -> tee
        if word in STOPWORDS:
            continue
        groups.append(SYNONYMS.get(word, [word]))
    return groups


def _score(p: dict, groups: list[list[str]]) -> int:
    fields = [
        (p["name"].lower(), 3), (p["garment_type"].lower(), 3),
        (" ".join(p["colors"]).lower(), 2), (" ".join(p["search_tags"]).lower(), 2),
        (p["description"].lower(), 1),
    ]
    score = 0
    for alternatives in groups:
        best = max((w for text, w in fields for alt in alternatives if alt in text), default=0)
        if best == 0:
            return 0  # every shopper word has to match somewhere
        score += best
    return score


def search_products(
    query: str = "",
    garment_type: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    size: str | None = None,
    search_id: str = "",
) -> tuple[SearchResult, list[str]]:
    """Returns what the model sees (best MAX_SEARCH_RESULTS) and every matching product_id, ranked.

    The full list is what a chat search puts on the web page (Problem 7).
    """
    products = load_products()
    if size:
        size = normalize_size(size) or size.upper()
    groups = _terms(query)
    filters = {k: v for k, v in
               {"garment_type": garment_type, "color": color, "max_price_usd": max_price, "size_in_stock": size}.items()
               if v is not None and v != ""}

    hits = []
    for p in products:
        if garment_type and not any(alt in p["garment_type"].lower() for g in _terms(garment_type) for alt in g):
            continue
        if color and not any(alt in " ".join(p["colors"]).lower() for g in _terms(color) for alt in g):
            continue
        if max_price is not None and p["price"] > max_price:
            continue
        if size and size not in _sizes_in_stock(p):
            continue
        score = _score(p, groups) if groups else 1
        if score:
            hits.append((score, p["total_stock"] > 0, p))

    hits.sort(key=lambda h: (h[0], h[1]), reverse=True)
    note = ""
    if not hits:
        note = "No products match. Tell the shopper we don't carry that, then try a broader search for something close."
    elif len(hits) > MAX_SEARCH_RESULTS:
        note = f"Showing the best {MAX_SEARCH_RESULTS} of {len(hits)}. Narrow with filters if needed."
    result = SearchResult(
        search_id=search_id, query=query, filters=filters, total_matches=len(hits),
        products=[_summary(p) for _, _, p in hits[:MAX_SEARCH_RESULTS]], note=note,
    )
    return result, [p["product_id"] for _, _, p in hits]


def get_product(product_id: str) -> ProductDetail | None:
    found = load_products(product_id)
    if not found:
        return None
    p = found[0]
    return ProductDetail(
        product_id=p["product_id"], name=p["name"], garment_type=p["garment_type"],
        description=p["description"], price_usd=p["price"], colors=p["colors"],
        stock_by_size=[SizeStock(size=i["size"], quantity_in_stock=i["quantity"], status=stock_status(i["quantity"]))
                       for i in p["inventory"]],
        sizes_in_stock=_sizes_in_stock(p), sold_out_sizes=_sold_out_sizes(p),
        total_in_stock=p["total_stock"], is_sold_out=p["total_stock"] == 0,
    )


def check_stock(product_id: str, size: str) -> StockCheck | None:
    """None if the product doesn't exist. Raises ValueError for something that isn't a size."""
    found = load_products(product_id)
    if not found:
        return None
    code = normalize_size(size)
    if code is None:
        raise ValueError(size)
    p = found[0]
    qty = next((i["quantity"] for i in p["inventory"] if i["size"] == code), None)
    status = stock_status(qty)
    others = [s for s in _sizes_in_stock(p) if s != code]
    note = {
        "sold out": f"Size {code} is SOLD OUT. Say so clearly, then offer {', '.join(others) or 'a similar item'}.",
        "low stock": f"Only {qty} left in {code}. It's fine to mention that it's selling out.",
        "size not offered": f"This item isn't offered in {code}. Offer {', '.join(others) or 'a similar item'}.",
    }.get(status, "")
    return StockCheck(
        product_id=product_id, name=p["name"], price_usd=p["price"], size=code,
        quantity_in_stock=qty or 0, status=status, other_sizes_in_stock=others, note=note,
    )


def suggest_products(text: str, limit: int = 3) -> list[ProductSummary]:
    """Closest products to a mistyped id or a product name, for 'did you mean' retries."""
    words = re.sub(r"[-_]", " ", text)
    for query in (words, " ".join(words.split()[:2]), words.split()[0] if words.split() else ""):
        if hits := search_products(query)[0].products:
            return hits[:limit]
    return []


# ---------------------------------------------------------------------------
# Model wiring: every call goes through the Portkey gateway (as in Homework 3)
# ---------------------------------------------------------------------------

def _load_dotenv(path: Path) -> bool:
    """Read KEY=value lines from .env without overriding anything already set."""
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))
    return True


def load_credentials() -> str:
    """Make PORTKEY_API_KEY available; returns where it came from. Never prints the key."""
    if os.getenv("PORTKEY_API_KEY"):
        return "environment"
    if _load_dotenv(HERE / ".env") and os.getenv("PORTKEY_API_KEY"):
        return "backend/.env"
    if _load_dotenv(HERE.parent / ".env") and os.getenv("PORTKEY_API_KEY"):
        return ".env (project root)"
    return "not found"


class MissingAPIKey(RuntimeError):
    pass


def build_model():
    """OpenAI-compatible chat model pointed at the course Portkey gateway. Returns (model, name)."""
    source = load_credentials()
    key = os.getenv("PORTKEY_API_KEY")
    if not key:
        raise MissingAPIKey(f"PORTKEY_API_KEY not found (looked in the environment, backend/.env and ./.env; got {source}).")

    from openai import AsyncOpenAI
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    headers = {"x-portkey-api-key": key}
    if virtual := os.getenv("PORTKEY_VIRTUAL_KEY"):
        headers["x-portkey-virtual-key"] = virtual
    if provider := os.getenv("PORTKEY_PROVIDER"):
        headers["x-portkey-provider"] = provider

    client = AsyncOpenAI(
        base_url=os.getenv("PORTKEY_BASE_URL", PORTKEY_BASE_URL_DEFAULT),
        api_key=key,
        default_headers=headers,
        max_retries=2,
    )
    name = os.getenv("PORTKEY_MODEL", MODEL_DEFAULT)
    return OpenAIChatModel(name, provider=OpenAIProvider(openai_client=client)), name
