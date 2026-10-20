"""My Closet and Wish List (Problem 9).

Two small tables, one row per saved item, owned by a logged-in shopper:

    closet_items     what the shopper already has (bought here, or marked "I own this")
    wishlist_items   what they want to buy later

Both store only IDs (product_id, optional size). Product details, prices and
stock are always read fresh from the catalogue when a list is shown, so a
wish-list item that sells out shows "sold out" the moment it does.

The routes live in main.py under /api/me/...; every one needs a logged-in session.
"""

from __future__ import annotations

import sqlite3

import tools
from db import connect_rw
from models import ListItem

LISTS = {"closet": "closet_items", "wishlist": "wishlist_items"}


def init_list_tables() -> None:
    with connect_rw() as con:
        for table in LISTS.values():
            con.execute(
                f"""create table if not exists {table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    product_id TEXT NOT NULL,
                    size TEXT,
                    added_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (product_id) REFERENCES catalogue(product_id)
                )"""
            )
            # One row per product+size per shopper (size '' when not given).
            con.execute(f"create unique index if not exists idx_{table}_unique on {table} (user_id, product_id, ifnull(size, ''))")


def list_items(kind: str, user_id: int) -> list[ListItem]:
    """Saved items, newest first, each with a fresh product card and the saved size's stock."""
    with connect_rw() as con:
        rows = con.execute(
            f"select id, product_id, size, added_at from {LISTS[kind]} where user_id = ? order by id desc", (user_id,)
        ).fetchall()
    cards = {c.product_id: c for c in tools.product_cards([r["product_id"] for r in rows], limit=10_000)}
    items = []
    for r in rows:
        card = cards.get(r["product_id"])
        if card is None:  # product removed from the catalogue
            continue
        size_status = None
        if r["size"]:
            size_status = "in stock" if r["size"] in card.sizes_in_stock else "sold out"
        items.append(ListItem(id=r["id"], size=r["size"], added_at=r["added_at"], product=card, size_status=size_status))
    return items


def add_item(kind: str, user_id: int, product_id: str, size: str | None) -> ListItem:
    """Add (or keep, if already there) an item. Raises KeyError for an unknown product, ValueError for a bad size."""
    if tools.get_product(product_id) is None:
        raise KeyError(product_id)
    if size:
        code = tools.normalize_size(size)
        if code is None:
            raise ValueError(size)
        size = code
    with connect_rw() as con:
        try:
            con.execute(f"insert into {LISTS[kind]} (user_id, product_id, size) values (?, ?, ?)", (user_id, product_id, size))
        except sqlite3.IntegrityError:
            pass  # already saved: adding twice is a no-op
        row_id = con.execute(
            f"select id from {LISTS[kind]} where user_id = ? and product_id = ? and ifnull(size, '') = ifnull(?, '')",
            (user_id, product_id, size),
        ).fetchone()["id"]
    return next(i for i in list_items(kind, user_id) if i.id == row_id)


def remove_item(kind: str, user_id: int, item_id: int) -> bool:
    """Remove one of the shopper's own items. False if it isn't theirs or doesn't exist."""
    with connect_rw() as con:
        cur = con.execute(f"delete from {LISTS[kind]} where id = ? and user_id = ?", (item_id, user_id))
        return cur.rowcount > 0


def move_to_closet(user_id: int, item_id: int) -> ListItem | None:
    """'I bought it': wish-list item -> closet. None if the item isn't theirs."""
    with connect_rw() as con:
        row = con.execute("select product_id, size from wishlist_items where id = ? and user_id = ?",
                          (item_id, user_id)).fetchone()
    if row is None:
        return None
    item = add_item("closet", user_id, row["product_id"], row["size"])
    remove_item("wishlist", user_id, item_id)
    return item


def product_ids(kind: str, user_id: int) -> list[str]:
    with connect_rw() as con:
        return [r[0] for r in con.execute(
            f"select product_id from {LISTS[kind]} where user_id = ? order by id desc", (user_id,))]
