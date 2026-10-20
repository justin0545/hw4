"""Personal recommendations (Problem 9).

Content-based: each product is described by a set of features, and products
are scored by how much they share with what the shopper has shown interest in.

Signals, strongest first:
    closet      items they own (their purchase history)           weight 3
    wish list   items they want                                    weight 2
    chat        products the assistant showed them in saved chats  weight 1

Features per product: garment family (hoodie, crewneck, tee, ...), colors,
theme words from the name (bulldog, hockey, Branford, ...) and search tags.
Each feature is weighted by how rare it is (inverse document frequency), so
"Yale" (on nearly everything) counts for little and "sailing" counts a lot.

Rules: never recommend something they already own or have wish-listed, only
items with stock, at most 2 per garment family so the list isn't all hoodies.
Every pick carries a reason naming the item that led to it.

No history (guests, new accounts): staff picks, labeled as such.
Pure Python over the catalogue; no model call, so it's fast and free.
"""

from __future__ import annotations

import math
import re
from collections import Counter

import chat_store
import shopper_lists
import tools
from models import ProductCard, Recommendation, Recommendations

SIGNAL_WEIGHTS = {"closet": 3.0, "wishlist": 2.0, "chat": 1.0}
MAX_PER_FAMILY = 2
STAFF_PICKS = ["basic-hoodie-big-yale", "2025-yale-vs-harvard-t-shirt", "champion-reverse-weave-crewneck",
               "boola-boola-t-shirt", "district-vit-hoodie-vintage-bulldog", "branford-1-4-zip",
               "brooks-brothers-bomber-jacket-yale", "big-yale-tri-blend-t-shirt"]

# Checked in order: "short-sleeve crew-neck t-shirt" is a tee, not a crewneck.
FAMILIES = [("quarter-zip", "quarter-zip"), ("1/4", "quarter-zip"), ("hood", "hoodie"), ("t-shirt", "tee"),
            ("tee", "tee"), ("long-sleeve", "long sleeve"), ("long sleeve", "long sleeve"), ("crew", "crewneck"),
            ("jacket", "jacket"), ("fleece", "jacket"), ("sweater", "jacket")]
NAME_STOPWORDS = {"yale", "t", "shirt", "the", "1", "4", "zip", "hoodie", "crewneck", "crew", "left", "chest",
                  "full", "and", "of", "jacket", "fleece", "sweater", "tee", "long", "sleeve", "vit", "district", "1/4"}


def family(garment_type: str) -> str:
    g = garment_type.lower()
    return next((fam for key, fam in FAMILIES if key in g), "other")


def features(p: dict) -> set[str]:
    words = {w for w in re.findall(r"[a-z]+", p["name"].lower()) if w not in NAME_STOPWORDS and len(w) > 2}
    return ({f"family:{family(p['garment_type'])}"}
            | {f"color:{c.lower()}" for c in p["colors"]}
            | {f"word:{w}" for w in words}
            | {f"tag:{t.lower()}" for t in p["search_tags"]})


def _idf(products: list[dict]) -> dict[str, float]:
    df = Counter(f for p in products for f in features(p))
    n = len(products)
    return {f: math.log((n + 1) / (c + 1)) for f, c in df.items()}


def _card(p: dict) -> ProductCard:
    return tools.product_cards([p["product_id"]])[0]


def signals(user_id: int) -> dict[str, list[str]]:
    """Product IDs behind each signal, most recent first."""
    return {
        "closet": shopper_lists.product_ids("closet", user_id),
        "wishlist": shopper_lists.product_ids("wishlist", user_id),
        "chat": chat_store.recent_shown_product_ids(user_id),
    }


def recommend(user_id: int | None, limit: int = 8) -> Recommendations:
    products = tools.load_products()
    by_id = {p["product_id"]: p for p in products}
    sig = signals(user_id) if user_id else {"closet": [], "wishlist": [], "chat": []}
    sig = {k: [pid for pid in dict.fromkeys(v) if pid in by_id] for k, v in sig.items()}
    exclude = set(sig["closet"]) | set(sig["wishlist"])
    based_on = {k: len(v) for k, v in sig.items()}

    if not any(sig.values()):
        picks = [by_id[pid] for pid in STAFF_PICKS if pid in by_id and by_id[pid]["total_stock"] > 0]
        return Recommendations(personalized=False, based_on=based_on, items=[
            Recommendation(product=_card(p), reason="Staff pick", score=0.0) for p in picks[:limit]])

    idf = _idf(products)
    feats = {p["product_id"]: features(p) for p in products}
    sources = [(kind, pid) for kind in ("closet", "wishlist", "chat") for pid in sig[kind]]

    scored = []
    for p in products:
        pid = p["product_id"]
        if pid in exclude or p["total_stock"] == 0:
            continue
        total, best, best_src = 0.0, 0.0, None
        for kind, src in sources:
            if src == pid:
                continue
            shared = feats[pid] & feats[src]
            sim = sum(idf.get(f, 0) for f in shared) / math.sqrt(len(feats[pid]) * len(feats[src]) or 1)
            contrib = SIGNAL_WEIGHTS[kind] * sim
            total += contrib
            if contrib > best:
                best, best_src = contrib, (kind, src)
        if total > 0 and best_src:
            scored.append((total, p, best_src))

    scored.sort(key=lambda s: s[0], reverse=True)
    picks, per_family = [], Counter()
    for total, p, (kind, src) in scored:
        fam = family(p["garment_type"])
        if per_family[fam] >= MAX_PER_FAMILY:
            continue
        per_family[fam] += 1
        name = by_id[src]["name"]
        reason = {"closet": f"Goes with your {name} (in your closet)",
                  "wishlist": f"Similar to {name} on your wish list",
                  "chat": f"Because you looked at {name} in chat"}[kind]
        picks.append(Recommendation(product=_card(p), reason=reason, score=round(total, 3)))
        if len(picks) >= limit:
            break
    return Recommendations(personalized=True, based_on=based_on, items=picks)


# ---------------------------------------------------------------------------
# Outfit builder (Problem 10): what goes with a piece
# ---------------------------------------------------------------------------
#
# Layering rules by garment family: for a base piece, which families pair with
# it and how to wear them together. Colors pair if they share a color or the
# partner is a Yale neutral (navy, white, gray) that goes with anything.
# Matching themes (same college, sport, bulldog...) score extra.

LAYERING = {
    "tee": [("quarter-zip", "over", "Zip a quarter-zip over the tee for chilly mornings"),
            ("hoodie", "over", "Throw a hoodie over it for game day"),
            ("jacket", "over", "Top it with a jacket for cold New Haven nights")],
    "long sleeve": [("quarter-zip", "over", "A quarter-zip over the long sleeve looks sharp"),
                    ("jacket", "over", "Add a jacket for the walk to class")],
    "hoodie": [("tee", "under", "Wear a tee underneath so you can lose the hoodie indoors"),
               ("jacket", "over", "Layer a jacket over the hoodie when it's freezing at the Bowl")],
    "crewneck": [("tee", "under", "A tee under the crewneck is the classic campus look"),
                 ("jacket", "over", "Add a jacket over the crewneck for tailgates")],
    "quarter-zip": [("tee", "under", "A tee under the quarter-zip keeps the collar clean"),
                    ("long sleeve", "under", "A long sleeve underneath for extra warmth")],
    "jacket": [("hoodie", "under", "A hoodie under the jacket is peak game-day warmth"),
               ("crewneck", "under", "A crewneck under the jacket is clean and warm"),
               ("tee", "under", "A tee underneath for milder days")],
    "other": [("tee", "under", "A tee underneath works with anything"),
              ("jacket", "over", "A jacket over it for cold days")],
}
NEUTRALS = ("navy", "white", "gray", "grey", "black")


def _colors_pair(a: list[str], b: list[str]) -> bool:
    a_l, b_l = [c.lower() for c in a], [c.lower() for c in b]
    shared = any(x == y or x in y or y in x for x in a_l for y in b_l)
    return shared or bool(b_l) and any(n in b_l[0] for n in NEUTRALS)  # partner's main color is a neutral


def suggest_outfit(product_id: str, owned_ids: set[str] | None = None, limit: int = 4) -> dict | None:
    """Pieces that go with one product: layering role, a styling tip, and whether they already own it.

    Returns None for an unknown product. Only in-stock partners. At most 2 per family.
    """
    products = tools.load_products()
    by_id = {p["product_id"]: p for p in products}
    base = by_id.get(product_id)
    if base is None:
        return None
    owned_ids = owned_ids or set()
    base_fam = family(base["garment_type"])
    rules = LAYERING.get(base_fam, LAYERING["other"])
    idf = _idf(products)
    base_words = {f for f in features(base) if f.startswith("word:")}

    picks = []
    for fam, role, tip in rules:
        cands = []
        for p in products:
            if p["product_id"] == product_id or family(p["garment_type"]) != fam or p["total_stock"] == 0:
                continue
            score = 1.0
            if _colors_pair(base["colors"], p["colors"]):
                score += 1.0
            shared = base_words & features(p)
            score += sum(idf.get(f, 0) for f in shared) / 2  # same college, sport, bulldog...
            if p["product_id"] in owned_ids:
                score += 3.0  # they already own it: the best pairing is free
            cands.append((score, p, shared))
        # Ties (common: many navy pieces) go to the best-stocked item, not the first alphabetically.
        cands.sort(key=lambda c: (c[0], c[1]["total_stock"]), reverse=True)
        for rank, (score, p, shared) in enumerate(cands[:2]):
            theme = ", ".join(sorted(f.split(":", 1)[1] for f in shared))
            picks.append({
                "product": tools._summary(p), "role": f"wear {role}", "tip": tip,
                "why_it_matches": (f"matching {theme} theme" if theme else
                                   "colors that go together" if _colors_pair(base["colors"], p["colors"]) else "classic pairing"),
                "already_owned": p["product_id"] in owned_ids, "score": round(score, 2), "rank": rank,
            })
    # Owned pieces first, then rotate through the layering options (best over-layer, best
    # under-layer, ...) so an outfit isn't four quarter-zips.
    picks.sort(key=lambda x: (not x["already_owned"], x["rank"], -x["score"]))
    for x in picks:
        del x["rank"]
    return {"base": tools._summary(base), "base_family": base_fam, "pieces": picks[:limit]}
