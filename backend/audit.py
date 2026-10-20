"""Append-only audit trail of agent-loop activity (Problem 12).

output/audit_trail.json is a JSON array with one AuditEntry per agent step:
time, run, shopper (user:<id> or guest), page, a redacted message preview, what
the model said, the tools it called (short args) and what they returned (short
summaries), token counts, and, on the last step, the stop reason.

Append-only: each write reads the existing list, adds the new entries and
atomically replaces the file. Nothing is ever removed, and an unreadable file
is set aside (never deleted) before a new list is started. Same pattern as
Homework 3. CAMPUS_CUSTOMS_AUDIT points tests at a throwaway file.
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from models import AuditEntry

ROOT = Path(__file__).resolve().parent.parent
AUDIT_PATH = Path(os.environ.get("CAMPUS_CUSTOMS_AUDIT", ROOT / "output" / "audit_trail.json"))
_lock = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clip(text: object, n: int = 200) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def short_args(args: dict) -> dict:
    return {k: (clip(v, 80) if isinstance(v, str) else v) for k, v in args.items()}


def append(entries: list[AuditEntry], path: Path | None = None) -> None:
    """Append entries without touching earlier ones."""
    if not entries:
        return
    path = path or AUDIT_PATH
    with _lock:
        existing: list = []
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8") or "[]")
                if not isinstance(existing, list):
                    existing = [existing]
            except json.JSONDecodeError:
                # Never silently drop history: keep the unreadable file aside, start a new list.
                path.replace(path.with_suffix(f".corrupt-{int(time.time())}.json"))
                existing = []
        existing.extend(e.model_dump(mode="json") for e in entries)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)


def summarize(tool_name: str, content: object) -> str:
    """One readable line per tool result, instead of the whole payload."""
    c = content
    try:
        if tool_name == "search_products":
            names = ", ".join(p.name for p in c.products[:3])
            return clip(f"{c.search_id}: {c.total_matches} matches for {c.query!r} {c.filters or ''} (top: {names})")
        if tool_name == "get_product":
            stock = " ".join(f"{s.size}:{s.quantity_in_stock}" for s in c.stock_by_size)
            return clip(f"{c.product_id} ${c.price_usd:g} stock {stock}")
        if tool_name == "check_stock":
            return clip(f"{c.product_id} size {c.size}: {c.quantity_in_stock} ({c.status})")
        if tool_name == "get_my_account":
            return "guest, no account" if isinstance(c, str) else f"account for {c.first_name} (email withheld from log)"
        if tool_name == "recommend_for_me":
            return clip(f"{len(c.items)} picks, personalized={c.personalized}, based_on={c.based_on}")
        if tool_name == "get_my_lists":
            return c if isinstance(c, str) else clip(f"closet {len(c['closet'])} items, wishlist {len(c['wishlist'])} items")
        if tool_name == "add_to_wish_list":
            return c if isinstance(c, str) else clip(f"saved {c.product.product_id} size {c.size}")
        if tool_name == "suggest_outfit":
            return clip(f"outfit for {c.base.product_id}: " + ", ".join(f"{p.product.product_id} ({p.role})" for p in c.pieces))
    except Exception:
        pass
    return clip(content)
