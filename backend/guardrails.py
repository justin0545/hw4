"""Code-level safety guardrails for the shop chat (Problem 12).

The prompt (prompts/prompt.md "Safety rules") tells the model how to behave.
These checks don't depend on the model obeying:

    scrub_input       redact card numbers, SSNs, passwords, phone numbers and emails
                      from the shopper's message BEFORE it reaches the model, the
                      saved chat history or the audit trail
    RateLimiter       at most N chat messages per minute per shopper/IP (cost + abuse)
    check_output      block a reply that would leak secrets (password hashes, the API
                      key, the system prompt) or echo card-like numbers
    MAX_REPLY_TOKENS  hard cap on how long a reply can be (no essays for off-topic asks)
"""

from __future__ import annotations

import os
import re
import time
from collections import defaultdict, deque

MAX_REPLY_TOKENS = 700          # a styling reply is ~60-150 tokens; this stops runaway essays
CHAT_MESSAGES_PER_MINUTE = 12   # per logged-in shopper, or per IP for guests

# ---- Input: redact sensitive data the shopper types -------------------------------

_CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_PASSWORD = re.compile(r"\b(pass(?:word|code|wd)?|pwd|pin)\b(\s*(?:is|=|:)\s*)(\S+)", re.IGNORECASE)
_PHONE = re.compile(r"(?<!\w)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\w)")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")


def _luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
        alt = not alt
    return total % 10 == 0


def scrub_input(text: str) -> tuple[str, list[str]]:
    """Return (text with sensitive data replaced by [redacted …], kinds found)."""
    found: list[str] = []

    def card(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            found.append("card number")
            return "[redacted card number]" + (" " if m.group(0)[-1] in " -" else "")  # keep the following space
        return m.group(0)

    text = _CARD.sub(card, text)
    if _SSN.search(text):
        found.append("SSN")
        text = _SSN.sub("[redacted SSN]", text)
    if _PASSWORD.search(text):
        found.append("password")
        text = _PASSWORD.sub(lambda m: f"{m.group(1)}{m.group(2)}[redacted password]", text)
    if _PHONE.search(text):
        found.append("phone number")
        text = _PHONE.sub("[redacted phone number]", text)
    if _EMAIL.search(text):
        found.append("email address")
        text = _EMAIL.sub("[redacted email]", text)
    return text, found


def redaction_note(found: list[str]) -> str:
    """Instruction for the model when something was redacted (it never sees the value)."""
    return (f"Note: the shopper typed a {', '.join(dict.fromkeys(found))}; it was removed before reaching you. "
            "Kindly tell them not to share that kind of information in chat, and don't ask for it.")


# ---- Rate limit --------------------------------------------------------------------

class RateLimiter:
    """Sliding one-minute window per key. In memory, so it resets when the server restarts."""

    def __init__(self, per_minute: int = CHAT_MESSAGES_PER_MINUTE):
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self._hits[key]
        while q and q[0] < now - 60:
            q.popleft()
        if len(q) >= self.per_minute:
            return False
        q.append(now)
        return True


# ---- Output: never let a reply leak secrets ----------------------------------------

_PROMPT_MARKERS = ("## Safety rules", "## Be a stylist, not a search box", "page_search_id", "Campus Customs Stylist\n\nYou are")


def check_output(reply: str) -> str | None:
    """Return a reason if the reply must not be shown, else None."""
    if "pbkdf2_sha256$" in reply:
        return "password hash in reply"
    key = os.environ.get("PORTKEY_API_KEY")
    if key and len(key) >= 8 and key in reply:
        return "API key in reply"
    if any(marker in reply for marker in _PROMPT_MARKERS):
        return "system prompt text in reply"
    if any(_luhn_ok(re.sub(r"\D", "", m.group(0))) and len(re.sub(r"\D", "", m.group(0))) >= 13 for m in _CARD.finditer(reply)):
        return "card-like number in reply"
    return None
