"""Lookup tools vs. the database: every price, description and stock number must match.

    cd backend && python test_tools.py

Reads the live database read-only and compares each tool result with a direct
SQL query, for all 102 products and all 612 product-size rows.
"""
import os as _os, tempfile as _tf; _os.environ.setdefault("CAMPUS_CUSTOMS_AUDIT", _os.path.join(_tf.mkdtemp(), "audit_trail.json"))  # tests never touch the real audit trail

import sqlite3

import tools
from db import DB_PATH

results = []


def check(name: str, cond: bool) -> None:
    results.append(cond)
    print(("PASS " if cond else "FAIL ") + name)


con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
catalogue = {pid: (name, desc, price) for pid, name, desc, price in
             con.execute("select product_id, name, description, price from catalogue")}
stock = {(pid, size): qty for pid, size, qty in con.execute("select product_id, size, quantity from inventory")}

# get_product: description, price, every size
bad = []
for pid, (name, desc, price) in catalogue.items():
    d = tools.get_product(pid)
    if d.name != name or d.description != desc or d.price_usd != price:
        bad.append(pid)
    for s in d.stock_by_size:
        if s.quantity_in_stock != stock[(pid, s.size)]:
            bad.append(f"{pid}/{s.size}")
    if d.total_in_stock != sum(q for (p, _), q in stock.items() if p == pid):
        bad.append(f"{pid}/total")
check(f"get_product matches the database for all {len(catalogue)} products ({len(bad)} mismatches)", not bad)

# check_stock: every product x size, quantity and status
bad = []
for (pid, size), qty in stock.items():
    r = tools.check_stock(pid, size)
    want = "sold out" if qty == 0 else "low stock" if qty <= 5 else "in stock"
    if r.quantity_in_stock != qty or r.status != want or r.price_usd != catalogue[pid][2]:
        bad.append(f"{pid}/{size}")
check(f"check_stock matches the database for all {len(stock)} product-size rows ({len(bad)} mismatches)", not bad)

sold_out = [(p, s) for (p, s), q in stock.items() if q == 0]
r = tools.check_stock(*sold_out[0])
check("sold-out size is labeled 'sold out' with a 'say so clearly' note",
      r.status == "sold out" and "SOLD OUT" in r.note and r.size not in r.other_sizes_in_stock)

# Size words shoppers use
check("size words normalize (medium->M, 2XL->XXL, extra small->XS)",
      [tools.normalize_size(s) for s in ["medium", "2XL", "Extra Small", " l ", "x-large"]] == ["M", "XXL", "XS", "L", "XL"])
check("check_stock accepts 'medium'", tools.check_stock("basic-hoodie-big-yale", "medium").size == "M")
try:
    tools.check_stock("basic-hoodie-big-yale", "huge")
    check("non-size is rejected", False)
except ValueError:
    check("non-size is rejected", True)

# Unknown products
check("unknown product_id returns None", tools.get_product("yale-mittens") is None and tools.check_stock("yale-mittens", "M") is None)
check("a name instead of an id gets close suggestions",
      tools.suggest_products("Basic Hoodie Big Yale")[0].product_id == "basic-hoodie-big-yale")

# search_products: summaries carry real prices and sizes; size filter is honest
hits = tools.search_products("hoodie", size="XXL")[0].products
check("search with size=XXL only returns items with XXL in stock", hits and all(stock[(h.product_id, "XXL")] > 0 for h in hits))
check("search summaries have real prices and sold-out sizes",
      all(h.price_usd == catalogue[h.product_id][2] and
          h.sold_out_sizes == [s for s in tools.SIZE_ORDER if stock[(h.product_id, s)] == 0] for h in hits))
check("max_price filter is respected", all(h.price_usd <= 40 for h in tools.search_products("", max_price=40)[0].products))

print(f"\n{sum(results)}/{len(results)} passed")
raise SystemExit(0 if all(results) else 1)
