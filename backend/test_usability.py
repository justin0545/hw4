"""Problem 9 usability features: My Closet, Wish List, recommendations, compressed images.

    cd backend && python test_usability.py

Runs against a throwaway copy of the seed database with a scripted stand-in
model for the agent-tool checks (no API key or network needed).
"""
import os as _os, tempfile as _tf; _os.environ.setdefault("CAMPUS_CUSTOMS_AUDIT", _os.path.join(_tf.mkdtemp(), "audit_trail.json"))  # tests never touch the real audit trail

import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The untouched original database: the backup made in Problem 4 if present, otherwise the
# data pack's campus_customs.db (what a grader has after unzipping data.zip).
SEED_DB = next(p for p in (ROOT / "data" / "campus_customs.seed.db", ROOT / "data" / "campus_customs.db") if p.exists())
tmp = Path(tempfile.mkdtemp()) / "test.db"
shutil.copy(SEED_DB, tmp)
os.environ["CAMPUS_CUSTOMS_DB"] = str(tmp)

from fastapi.testclient import TestClient  # noqa: E402
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart, ToolReturnPart  # noqa: E402
from pydantic_ai.models.function import AgentInfo, FunctionModel  # noqa: E402

import agent  # noqa: E402
import images  # noqa: E402
import main  # noqa: E402

results = []


def check(name: str, cond: bool) -> None:
    results.append(cond)
    print(("PASS " if cond else "FAIL ") + name)


def scripted(tool: str, args: dict, page: bool = False):
    """Calls one tool, then replies (optionally putting the tool's search on the page)."""

    def fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        returns = [p for m in messages for p in m.parts if isinstance(p, ToolReturnPart)]
        if not returns:
            return ModelResponse(parts=[ToolCallPart(tool, args)])
        out = {"message": "Done!", "product_ids": []}
        if page:
            out |= {"page_search_id": returns[0].content.search_id, "page_title": "Recommended for you"}
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, out)])

    return FunctionModel(fn)


with TestClient(main.app) as c:
    # ---- Guests ----
    check("closet needs a login (401)", c.get("/api/me/closet").status_code == 401)
    check("wish list needs a login (401)", c.post("/api/me/wishlist", json={"product_id": "boola-boola-t-shirt"}).status_code == 401)
    recs = c.get("/api/recommendations").json()
    check("guests get staff picks, labeled as such", not recs["personalized"] and recs["items"] and recs["items"][0]["reason"] == "Staff pick")

    # ---- 1. My Closet ----
    c.post("/api/auth/login", json={"email": "test@campuscustoms.yale.edu", "password": "password"})
    r = c.post("/api/me/closet", json={"product_id": "basic-hoodie-big-yale", "size": "medium"})
    check("add to closet (size word normalized to M)", r.status_code == 201 and r.json()["size"] == "M")
    c.post("/api/me/closet", json={"product_id": "basic-hoodie-big-yale", "size": "M"})
    closet = c.get("/api/me/closet").json()
    check("adding the same item+size twice keeps one row", len(closet) == 1)
    check("closet items carry a fresh product card", closet[0]["product"]["name"] == "Basic Hoodie Big Yale" and closet[0]["product"]["price"] == 68.0)
    check("unknown product is rejected (404)", c.post("/api/me/closet", json={"product_id": "yale-mittens"}).status_code == 404)
    check("bad size is rejected (422)", c.post("/api/me/closet", json={"product_id": "boola-boola-t-shirt", "size": "huge"}).status_code == 422)

    # ---- 2. Wish List ----
    w = c.post("/api/me/wishlist", json={"product_id": "boola-boola-t-shirt", "size": "L"}).json()
    check("wish-list item shows its saved size is sold out (Boola Boola L = 0)", w["size_status"] == "sold out")
    w2 = c.post("/api/me/wishlist", json={"product_id": "district-vit-hoodie-vintage-sailor-bulldog", "size": "M"}).json()
    check("wish-list item in stock shows 'in stock'", w2["size_status"] == "in stock")
    moved = c.post(f"/api/me/wishlist/{w2['id']}/move-to-closet").json()
    check("'I bought it' moves a wish-list item into the closet",
          moved["product"]["product_id"] == "district-vit-hoodie-vintage-sailor-bulldog"
          and len(c.get("/api/me/wishlist").json()) == 1 and len(c.get("/api/me/closet").json()) == 2)

    # Another shopper can't touch these
    c.post("/api/auth/logout")
    c.post("/api/auth/signup", json={"first_name": "Other", "last_name": "Shopper", "email": "other@example.test",
                                     "password": "Password123", "confirm_password": "Password123"})
    check("another shopper sees an empty closet", c.get("/api/me/closet").json() == [])
    check("another shopper can't delete someone else's item (404)", c.delete(f"/api/me/wishlist/{w['id']}").status_code == 404)
    c.post("/api/auth/logout")
    c.post("/api/auth/login", json={"email": "test@campuscustoms.yale.edu", "password": "password"})
    check("...and the item is still there", len(c.get("/api/me/wishlist").json()) == 1)

    # ---- 3. Recommendations ----
    recs = c.get("/api/recommendations").json()
    owned = {"basic-hoodie-big-yale", "district-vit-hoodie-vintage-sailor-bulldog", "boola-boola-t-shirt"}
    ids = [r["product"]["product_id"] for r in recs["items"]]
    check("recommendations are personalized from closet, wish list and chat",
          recs["personalized"] and recs["based_on"]["closet"] == 2 and recs["based_on"]["wishlist"] == 1 and recs["based_on"]["chat"] > 0)
    check("never recommends what they own or wish-listed", not (owned & set(ids)))
    check("only in-stock items", all(r["product"]["total_stock"] > 0 for r in recs["items"]))
    check("every pick has a reason naming what led to it",
          all(any(k in r["reason"] for k in ("closet", "wish list", "chat")) for r in recs["items"]))
    fams = [main.recommend.family(r["product"]["garment_type"]) for r in recs["items"]]
    check("at most 2 picks per garment family", all(fams.count(f) <= 2 for f in fams))
    check("a vintage bulldog item is recommended (they own the Sailor Bulldog Hoodie)",
          any("bulldog" in r["product"]["name"].lower() for r in recs["items"]))

    agent._model = scripted("recommend_for_me", {"limit": 6}, page=True)
    data = c.post("/api/chat", json={"message": "What would you recommend for me?"}).json()
    check("agent tool recommend_for_me can fill the page with the picks",
          data["page_results"] and data["page_results"]["title"] == "Recommended for you" and len(data["page_results"]["products"]) == 6)

    agent._model = scripted("add_to_wish_list", {"product_id": "champion-reverse-weave-crewneck", "size": "L"})
    c.post("/api/chat", json={"message": "add this to my wish list in large",
                              "page": {"path": "/products/champion-reverse-weave-crewneck", "product_id": "champion-reverse-weave-crewneck"}})
    check("agent tool add_to_wish_list saves to the shopper's wish list",
          any(i["product"]["product_id"] == "champion-reverse-weave-crewneck" and i["size"] == "L" for i in c.get("/api/me/wishlist").json()))

    # ---- 4. Compressed images ----
    p = c.get("/api/products/basic-hoodie-big-yale").json()
    check("product API points cards at /media/card/ and the detail page at /media/large/",
          p["image_url"].startswith("/media/card/") and p["image_url_large"].startswith("/media/large/"))
    card, orig = c.get(p["image_url"]), c.get(p["image_url_original"])
    check("compressed card image is served as WebP", card.status_code == 200 and card.headers["content-type"] == "image/webp")
    check("card image is much smaller than the original", len(card.content) < len(orig.content) * 0.5)
    check("images get a one-week browser cache header", card.headers.get("cache-control") == "public, max-age=604800")
    r = images.report()
    check("all 102 products have all three compressed versions",
          all(len(list((images.OUT_DIR / v).glob("*"))) >= 102 for v in images.VARIANTS))
    check("whole catalogue grid is at least 75% lighter", r["card_kb"] < r["original_kb"] * 0.25)
    check("model-ready images cut estimated vision tokens by over half", r["vision_tokens_model_variant"] < r["vision_tokens_original"] * 0.5)

print(f"\n{sum(results)}/{len(results)} passed")
raise SystemExit(0 if all(results) else 1)
