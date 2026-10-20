"""Saved chat history for logged-in shoppers (Problem 8).

Stored in the existing chat_messages table, one row per message:

    id                 INTEGER  primary key, gives the order
    user_id            INTEGER  -> users.id (only logged-in shoppers are saved)
    role               TEXT     'user' or 'assistant'
    content            TEXT     the message text
    products_json      TEXT     assistant rows: the chat cards shown (list of product dicts)
    page_results_json  TEXT     assistant rows: the search put on the page, if any   [added in Problem 8]
    created_at         TEXT     UTC timestamp

Only product IDs are read back from the JSON columns. Cards are rebuilt from
the catalogue on reload, so a returning shopper sees today's prices and stock,
and old seed rows (which stored full product records) load the same way.
"""

from __future__ import annotations

import json

import tools
from db import connect_rw
from models import (
    MAX_HISTORY_MESSAGES,
    MAX_PAGE_RESULTS,
    ChatReply,
    ChatTurn,
    HistoryMessage,
    PageResults,
)

MAX_DISPLAY_MESSAGES = 50  # how much of the past conversation the widget shows on return


def init_chat_tables() -> None:
    """Add the page_results_json column and a per-user index if they're missing (safe to run every start)."""
    with connect_rw() as con:
        cols = {r["name"] for r in con.execute("pragma table_info(chat_messages)")}
        if "page_results_json" not in cols:
            con.execute("alter table chat_messages add column page_results_json TEXT")
        con.execute("create index if not exists idx_chat_messages_user on chat_messages (user_id, id)")


def save_turn(user_id: int, message: str, reply: ChatReply) -> None:
    """Save the shopper's message and the assistant's reply."""
    cards = json.dumps([c.model_dump() for c in reply.products]) if reply.products else None
    page = None
    if reply.page_results:
        p = reply.page_results
        page = json.dumps({"title": p.title, "query": p.query, "filters": p.filters,
                           "product_ids": [c.product_id for c in p.products]})
    with connect_rw() as con:
        con.execute("insert into chat_messages (user_id, role, content) values (?, 'user', ?)", (user_id, message))
        con.execute(
            "insert into chat_messages (user_id, role, content, products_json, page_results_json) "
            "values (?, 'assistant', ?, ?, ?)",
            (user_id, reply.reply, cards, page),
        )


def _recent_rows(user_id: int, limit: int) -> list[dict]:
    with connect_rw() as con:
        rows = con.execute(
            "select id, role, content, products_json, page_results_json, created_at from chat_messages "
            "where user_id = ? order by id desc limit ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def _product_ids(products_json: str | None) -> list[str]:
    try:
        items = json.loads(products_json) if products_json else []
        return [p["product_id"] for p in items if isinstance(p, dict) and "product_id" in p]
    except (ValueError, TypeError):
        return []


def _page(page_json: str | None) -> PageResults | None:
    try:
        data = json.loads(page_json) if page_json else None
    except ValueError:
        return None
    if not data or not data.get("product_ids"):
        return None
    cards = tools.product_cards(data["product_ids"], limit=MAX_PAGE_RESULTS)
    return PageResults(title=data.get("title", "Results"), query=data.get("query", ""),
                       filters=data.get("filters", {}), total_matches=len(cards), products=cards)


def load_for_agent(user_id: int) -> list[ChatTurn]:
    """The agent's memory for a logged-in shopper: their last MAX_HISTORY_MESSAGES saved messages."""
    return [
        ChatTurn(role=r["role"], content=r["content"][: 8000],
                 product_ids=_product_ids(r["products_json"])[:6] if r["role"] == "assistant" else [])
        for r in _recent_rows(user_id, MAX_HISTORY_MESSAGES)
        if r["role"] in ("user", "assistant")
    ]


def load_for_display(user_id: int) -> list[HistoryMessage]:
    """What the chat widget shows when a logged-in shopper comes back. Cards use current data."""
    return [
        HistoryMessage(
            role=r["role"], content=r["content"], created_at=r["created_at"],
            products=tools.product_cards(_product_ids(r["products_json"])),
            page_results=_page(r["page_results_json"]),
        )
        for r in _recent_rows(user_id, MAX_DISPLAY_MESSAGES)
        if r["role"] in ("user", "assistant")
    ]


def count_messages(user_id: int) -> int:
    with connect_rw() as con:
        return con.execute("select count(*) from chat_messages where user_id = ?", (user_id,)).fetchone()[0]


def recent_shown_product_ids(user_id: int, limit: int = MAX_DISPLAY_MESSAGES) -> list[str]:
    """Products the assistant showed this shopper as chat cards, most recent first (for recommendations)."""
    ids: list[str] = []
    for r in reversed(_recent_rows(user_id, limit)):
        if r["role"] == "assistant":
            ids.extend(_product_ids(r["products_json"]))
    return list(dict.fromkeys(ids))
