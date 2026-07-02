"""
test_agent.py - deterministic test suite for the agent brain.
Run:  python3 tests/test_agent.py
Exits non-zero if anything fails. No network / no model needed.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from intelligence import agent

PASS, FAIL = 0, 0
FAILURES = []


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  ok  - %s" % name)
    else:
        FAIL += 1
        FAILURES.append("%s   %s" % (name, detail))
        print("  XX  - %s   %s" % (name, detail))


# ── 1) PARAMETER EXTRACTION ("the smartness") ──────────────────────────────────
print("\n[parameter extraction]")

p = agent.extract_params("I want to add apple juice cocktail as a drink and bring it to the menu")
check("name = Apple Juice Cocktail", p["product_name"] == "Apple Juice Cocktail", p["product_name"])
check("type = drink", p["type"] == "drink", p["type"])
check("price auto-filled", p["price"] is not None and p["price_auto"] is True, str(p))
check("category pref starts Soft Drinks", p["category_pref"][0] == "Soft Drinks", str(p["category_pref"]))
check("is_add flagged", p["is_add"] is True, str(p["is_add"]))

p = agent.extract_params("add a burger for 8.50")
check("name = Burger", p["product_name"] == "Burger", p["product_name"])
check("type = food", p["type"] == "food", p["type"])
check("price = 8.50 (given)", p["price"] == "8.50" and p["price_auto"] is False, str(p))

p = agent.extract_params("create a product called Espresso Martini priced at 9")
check("name = Espresso Martini", p["product_name"] == "Espresso Martini", p["product_name"])
check("price = 9.00", p["price"] == "9.00", p["price"])
check("type drink (martini)", p["type"] == "drink", p["type"])

p = agent.extract_params("add green tea")
check("name = Green Tea", p["product_name"] == "Green Tea", p["product_name"])
check("tea -> drink", p["type"] == "drink", p["type"])
check("no price -> auto drink 3.50", p["price"] == "3.50" and p["price_auto"], str(p))

p = agent.extract_params("add allergens to my pizza")
check("allergen request is NOT add-product", p["is_add"] is False, str(p["is_add"]))


# ── 2) ROUTING (single guide) ──────────────────────────────────────────────────
print("\n[routing - single]")

def route1(q):
    return agent.plan(q)

cases_single = [
    ("I want to add apple juice cocktail as a drink and bring it to the menu", 1),
    ("how do I stop tickets printing automatically in the kitchen", 21),
    ("add allergens to my pizza", 6),
    ("create a combo deal of fries and a drink", 4),
    ("make a fixed price french menu", 16),
    ("add a new drinks product group", 12),
    ("give my product multiple barcodes", 25),
    ("assign a plu to a product", 11),
    ("rearrange my menu with submenus", 19),
    ("assign price levels to my downtown store", 20),
    ("search for a product", 5),
    ("set which menu shows in which area and time", 22),
    ("activate regime forfettario", 8),
    ("set up a production order", 9),
    ("add a packaging profile for takeaway", 23),
    ("change the vat for food products", 24),
    ("assign sales and restrictions to a product group", 3),
    ("add a happy hour discount", 18),
    ("bulk edit several products at once", 2),
    ("create a price set pricing rule", 13),
    ("add a price level for takeaway", 14),
    ("add a derived menu from a base menu", 15),
]
for q, exp in cases_single:
    pl = route1(q)
    got = pl.get("primary")
    check("'%s' -> Q%d" % (q[:42], exp),
          pl["action"] in ("single", "merge") and got == exp,
          "got action=%s primary=%s guides=%s" % (pl["action"], got, pl.get("guides")))


# ── 3) MULTI-GUIDE MERGE ───────────────────────────────────────────────────────
print("\n[routing - merge]")

pl = route1("add a burger and only show it during lunch")
check("burger+lunch -> merge Q1+Q17", pl["action"] == "merge" and pl["guides"] == [1, 17],
      str(pl.get("guides")))

pl = route1("add apple juice cocktail as a drink, on the lunch menu, with allergens")
check("juice+lunch+allergens -> merge Q1+Q6+Q17",
      pl["action"] == "merge" and pl["guides"] == [1, 6, 17], str(pl.get("guides")))

pl = route1("add apple juice cocktail as a drink and bring it to the menu")
check("add+to-menu stays single Q1 (menu builtin)",
      pl["action"] == "single" and pl["guides"] == [1], str(pl.get("guides")))


# ── 4) CLARIFY ─────────────────────────────────────────────────────────────────
print("\n[clarify]")
pl = route1("how do I change a price")
check("'change a price' -> clarify", pl["action"] == "clarify", str(pl.get("action")))
check("clarify gives 3 options", len(pl.get("options", [])) == 3, str(pl.get("options")))


# ── 5) NO MATCH ────────────────────────────────────────────────────────────────
print("\n[no match]")
pl = route1("how do I do my taxes")
check("'do my taxes' -> none (no false Q8)", pl["action"] == "none", str(pl.get("action")))

pl = route1("what is the weather today")
check("off-topic -> none", pl["action"] == "none", str(pl.get("action")))


# ── 6) ANSWER ASSEMBLY uses the user's product + is grounded ───────────────────
print("\n[answer assembly]")
res = agent.answer("I want to add apple juice cocktail as a drink and bring it to the menu")
check("answer mentions Apple Juice Cocktail", "Apple Juice Cocktail" in res["answer"], "")
check("answer has numbered steps", "1." in res["answer"] and "2." in res["answer"], "")
check("recipe_vars NAME set", res["recipe_vars"].get("NAME") == "Apple Juice Cocktail",
      str(res.get("recipe_vars")))
check("recipe_vars PRICE set", bool(res["recipe_vars"].get("PRICE")), str(res.get("recipe_vars")))
check("primary qid = 1", res["qid"] == 1, str(res["qid"]))

res = agent.answer("add a burger and only show it during lunch")
check("merged answer has both guide titles",
      "First" in res["answer"] and "Then" in res["answer"], "")
check("merged sources = 2", len(res["sources"]) == 2, str(res["sources"]))


# ── 7) EXTRA: messy / unseen phrasings (generalisation) ────────────────────────
print("\n[generalisation - messy phrasings]")
extra = [
    ("i wanna add a mango lassi as a drink", 1, "single"),
    ("add a cheeseburger priced 12 and only show during dinner", 1, "merge"),
    ("put gluten info on my pasta", 6, "single"),
    ("how to turn off automatic ticket printing", 21, "single"),
    ("i need to add barcodes to a product", 25, "single"),
    ("set up a 3 course fixed price menu", 16, "single"),
    ("create a new product group for desserts", 12, "single"),
    ("assign a price level to my store downtown", 20, "single"),
    ("add iced latte for 4.5", 1, "single"),
    ("make a combo of burger fries and a coke", 4, "single"),
    ("change the price of my coffee", None, "clarify"),
    ("how is the stock market today", None, "none"),
    # ── added after independent 30-question audit (routing fixes) ──
    ("can you help me put a new espresso martini on the drinks menu", 1, "single"),
    ("put a caesar salad on the food menu", 1, "single"),
    ("how do I stop the kitchen from auto printing tickets", 21, "single"),
    ("I'd like to disable ticket printing in the kitchen", 21, "single"),
    ("stop printing tickets automatically", 21, "single"),
    ("make a prix fixe dinner menu", 16, "single"),
    ("create a lunch menu with a fixed price", 16, "single"),
    ("register a new IPA beer for 6", 1, "single"),
    ("set a price level for my store", 20, "single"),
    # ── added after 50-question HTTP chatbot smoke test ──
    ("bundle multiple products into one item", 4, "single"),
    ("make products available only during happy hour", 17, "single"),
    # ── added after round-2 (50 fresh questions) ──
    ("how do I create a new menu item for a smoothie", 1, "single"),
    ("how to change product names directly in the overview list", 2, "single"),
    ("I need to update the details of an existing product", 7, "single"),
    ("how do I manage all my products", 10, "single"),
    ("I don't want tickets to print automatically", 21, "single"),
    ("assign a menu to a specific area", 22, "single"),
    ("add a salad and give it a barcode", 1, "merge"),
    ("combine several products into one combo", 4, "single"),
]
for q, exp, act in extra:
    pl = agent.plan(q)
    ok = pl["action"] == act and (exp is None or pl.get("primary") == exp)
    check("'%s' -> %s/%s" % (q[:38], act, exp), ok,
          "got action=%s primary=%s" % (pl["action"], pl.get("primary")))


# ── summary ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("RESULT: %d passed, %d failed (of %d)" % (PASS, FAIL, PASS + FAIL))
if FAILURES:
    print("\nFAILURES:")
    for f in FAILURES:
        print("  -", f)
sys.exit(1 if FAIL else 0)
