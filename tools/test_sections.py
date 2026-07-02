"""
test_sections.py - verify the chatbot routes RANDOM questions section-specifically
and never intersects sections.

For each query we call agent.plan() (pure routing, no files needed) and check:
  * the classified section matches the expected one
  * EVERY routed/merged guide lives in that one section (no cross-section bleed)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from intelligence import agent

# (query, expected_section) - deliberately varied / random / paraphrased wording,
# the way a real user might type, NOT the exact guide titles.
CASES = [
    # ---- Products (Q1-25) ----
    ("I need to put a new latte on the menu", "Products"),
    ("rename a few products quickly in the list view", "Products"),
    ("restrict when this product can be sold", "Products"),
    ("make a meal deal that combines a burger and fries", "Products"),
    ("I can't find a product, how do I search for it", "Products"),
    ("flag that this dish contains peanuts", "Products"),
    ("edit the details of an existing dish", "Products"),
    ("set the kitchen preparation order", "Products"),
    ("assign a PLU to a drink", "Products"),
    ("make a new category for desserts", "Products"),
    ("create a menu derived from another one", "Products"),
    ("build a fixed price 3 course menu", "Products"),
    ("only show the lunch items at midday", "Products"),
    ("run a 20% off happy hour", "Products"),
    ("rearrange the menu and add a submenu", "Products"),
    ("link a price level to a specific store", "Products"),
    ("show a different menu in the terrace area at certain times", "Products"),
    ("add a deposit packaging profile for takeaway cups", "Products"),
    ("lower the VAT on food items", "Products"),
    ("stop the kitchen tickets printing automatically", "Products"),
    ("let me scan an extra barcode for a product", "Products"),
    # ---- Self-service (Q26-38) ----
    ("customers should be able to pay when they collect their order", "Self-service"),
    ("set the hours my self-service is open", "Self-service"),
    ("restyle the self-service QR shop", "Self-service"),
    ("suggest extra items at the kiosk checkout", "Self-service"),
    ("add the legal imprint to my web shop", "Self-service"),
    ("change the look of the kiosk screen", "Self-service"),
    ("adjust my DISH Payment settings", "Self-service"),
    ("make the webshop my own", "Self-service"),
    ("show separate eat-in and takeaway menus on the kiosk", "Self-service"),
    ("generate QR codes for table ordering", "Self-service"),
    ("support buzzers so guests know their food is ready", "Self-service"),
    # ---- Payment (Q39-44) ----
    ("add a cash payment method", "Payment"),
    ("manage the card machines and EFT devices", "Payment"),
    ("set up a stand-alone EFT terminal", "Payment"),
    ("let regulars pay on account", "Payment"),
    ("set up a smart voucher as a payment option", "Payment"),
]

# Cross-section requests: we don't assert WHICH section wins, only that the answer
# stays inside a SINGLE section (no intersection).
CROSS = [
    "add a cheeseburger to the menu and turn on cross-selling at the kiosk",
    "create QR codes and also add a payment method",
    "set up a happy hour discount and configure a smart voucher",
]

# Within-section MERGE must still work: multi-part requests inside one section
# should stitch several guides together (and all stay in that section).
MERGE = [
    ("add a mojito as a drink and only show it during happy hour", "Products"),
    ("add a cheeseburger and mark its allergens", "Products"),
    ("create a price set and a price level", "Products"),
]

# Single-product price changes -> must route to the list-view edit guide (Q2),
# extract the product + amount, and NOT show the 3-way clarify. (query, name, amount)
PRICE_EDITS = [
    ("change the price of water to 20 euros", "Water", "20.00"),
    ("set the price of cola to 3.50", "Cola", "3.50"),
    ("update the price of the burger to 12", "Burger", "12.00"),
    ("make the cappuccino cost 4 euros", "Cappuccino", "4.00"),
    ("change water's price to 20", "Water", "20.00"),
    ("lower the price of fries to 2.50", "Fries", "2.50"),
    ("raise the beer price to 6", "Beer", "6.00"),
    ("edit the price of espresso to 2.20", "Espresso", "2.20"),
    ("change the price of the latte", "Latte", None),   # no amount, still Q2
]

# Genuinely vague price requests -> SHOULD still show the clarify (not guess).
CLARIFY = [
    "I want to change prices",
    "how do I change the price",
]


def sec_of_guides(guides):
    return sorted({agent.section_of(g) for g in guides})


def main():
    passed = failed = 0
    print("=" * 78)
    print("SECTION-SPECIFIC ROUTING  (expected vs. actual, + all-guides-in-one-section)")
    print("=" * 78)
    for q, expected in CASES:
        pl = agent.plan(q)
        guides = pl.get("guides", []) or []
        secs = sec_of_guides(guides)
        # A real pass requires: a guide WAS found, all guides sit in ONE section,
        # and that section is the expected one.
        in_one = len(secs) == 1 and secs[0] is not None
        ok = bool(guides) and in_one and secs[0] == expected and pl.get("section") == expected
        passed += ok
        failed += (not ok)
        flag = "OK " if ok else "XX "
        print("%s [%s] guides=%s -> %s | want=%s | %s"
              % (flag, pl.get("section"), guides, secs, expected, q))
    print("-" * 78)
    print("NO-INTERSECTION CHECK on cross-section requests:")
    for q in CROSS:
        pl = agent.plan(q)
        guides = pl.get("guides", [])
        secs = sec_of_guides(guides)
        one_section = len(secs) == 1 and secs[0] is not None
        passed += one_section
        failed += (not one_section)
        flag = "OK " if one_section else "XX "
        print("%s section=%s guides=%s -> %s | %s"
              % (flag, pl.get("section"), guides, secs, q))
    print("-" * 78)
    print("WITHIN-SECTION MERGE still works (>=2 guides, all in one section):")
    for q, expected in MERGE:
        pl = agent.plan(q)
        guides = pl.get("guides", []) or []
        secs = sec_of_guides(guides)
        ok = len(guides) >= 2 and len(secs) == 1 and secs[0] == expected
        passed += ok
        failed += (not ok)
        flag = "OK " if ok else "XX "
        print("%s [%s] guides=%s -> %s | want>=2 in %s | %s"
              % (flag, pl.get("section"), guides, secs, expected, q))
    print("-" * 78)
    print("SINGLE-PRODUCT PRICE CHANGE -> list-view edit (Q2), product+amount extracted:")
    for q, name, amt in PRICE_EDITS:
        pl = agent.plan(q)
        p = pl.get("params", {}) or {}
        guides = pl.get("guides", []) or []
        name_ok = (p.get("product_name") == name)
        amt_ok = (amt is None) or (p.get("price") == amt and not p.get("price_auto"))
        ok = pl.get("action") == "single" and guides == [2] and name_ok and amt_ok
        passed += ok
        failed += (not ok)
        flag = "OK " if ok else "XX "
        print("%s action=%s guides=%s name=%r price=%r(auto=%s) | want Q2 %r/%r | %s"
              % (flag, pl.get("action"), guides, p.get("product_name"),
                 p.get("price"), p.get("price_auto"), name, amt, q))
    print("-" * 78)
    print("VAGUE price requests -> still CLARIFY (don't guess):")
    for q in CLARIFY:
        pl = agent.plan(q)
        ok = pl.get("action") == "clarify"
        passed += ok
        failed += (not ok)
        flag = "OK " if ok else "XX "
        print("%s action=%s | want=clarify | %s" % (flag, pl.get("action"), q))
    print("=" * 78)
    print("PASSED %d / %d" % (passed, passed + failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main()
    text = buf.getvalue()
    print(text)
    (Path(__file__).resolve().parent / "test_sections_out.txt").write_text(text, encoding="utf-8")
    raise SystemExit(rc)
