"""
chat_smoketest.py - drives the REAL chatbot endpoint (server.app /api/chat) with 50
varied, randomly-phrased questions, exactly as a user typing into the chat box would.
For each it checks the routing the chatbot returned (action / guide id / merged guides)
and logs the actual answer text. Writes a full transcript + a PASS/FAIL summary.

Run:  python -m tools.chat_smoketest
Output: output/chat_smoketest_results.txt   (also printed to console)
"""
import sys, json, io
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import server  # noqa

client = server.app.test_client()

# (question, expected_primary_qid_or_None, expected_action, expected_guides_or_None)
TESTS = [
    # ---- Q1 add product (various phrasings) ----
    ("add apple juice cocktail as a drink and put it on the menu", 1, "single", None),
    ("create a new burger for 9.50", 1, "single", None),
    ("i wanna add an iced latte", 1, "single", None),
    ("put a caesar salad on the food menu", 1, "single", None),
    ("register a new IPA beer for 6", 1, "single", None),
    # ---- Q2 list view ----
    ("edit several products at once in the list", 2, "single", None),
    ("quick inline edit of product names", 2, "single", None),
    # ---- Q3 restrictions ----
    ("restrict a product so it can only be sold to adults", 3, "single", None),
    ("assign sales restrictions to an item", 3, "single", None),
    # ---- Q4 composites ----
    ("make a combo deal of burger fries and a drink", 4, "single", None),
    ("bundle multiple products into one item", 4, "single", None),
    # ---- Q5 search/filter ----
    ("search and filter my products", 5, "single", None),
    ("how do I locate a product quickly", 5, "single", None),
    # ---- Q6 allergens ----
    ("add allergens to my pizza", 6, "single", None),
    ("tag gluten and nuts on a dish", 6, "single", None),
    # ---- Q7 adjust details ----
    ("adjust product details", 7, "single", None),
    ("modify a product's information", 7, "single", None),
    # ---- Q8 regime forfettario ----
    ("enable the italian regime forfettario", 8, "single", None),
    # ---- Q9 production order ----
    ("set the kitchen production order for prep", 9, "single", None),
    # ---- Q10 manage products ----
    ("manage my products", 10, "single", None),
    # ---- Q11 PLU ----
    ("assign a plu number to a product", 11, "single", None),
    # ---- Q12 product group ----
    ("create a new product group for desserts", 12, "single", None),
    ("add a category called sides", 12, "single", None),
    # ---- Q13 price set ----
    ("create a price set", 13, "single", None),
    ("add a pricing rule set", 13, "single", None),
    # ---- Q14 price level ----
    ("add a new price level", 14, "single", None),
    # ---- Q15 derived menu ----
    ("create a derived menu from a base menu", 15, "single", None),
    # ---- Q16 fixed-price / french ----
    ("make a prix fixe dinner menu", 16, "single", None),
    ("set up a fixed price menu", 16, "single", None),
    # ---- Q17 time periods ----
    ("add a time period for lunch", 17, "single", None),
    ("make products available only during happy hour", 17, "single", None),
    # ---- Q18 promotions ----
    ("set up a happy hour discount", 18, "single", None),
    ("add a promotion", 18, "single", None),
    # ---- Q19 arrange menus ----
    ("arrange my menu into submenus", 19, "single", None),
    # ---- Q20 price level to store ----
    ("assign a price level to my downtown store", 20, "single", None),
    ("set the store price level", 20, "single", None),
    # ---- Q21 ticket printing ----
    ("stop tickets printing automatically", 21, "single", None),
    ("disable ticket printing in the kitchen", 21, "single", None),
    ("how do I stop the kitchen from auto printing tickets", 21, "single", None),
    # ---- Q22 menus per area/time ----
    ("which menu shows in the bar area", 22, "single", None),
    ("assign a menu to a specific area and time", 22, "single", None),
    # ---- Q23 packaging ----
    ("set up a takeaway packaging deposit", 23, "single", None),
    ("add a packaging profile", 23, "single", None),
    # ---- Q24 VAT food ----
    ("change the vat for food items", 24, "single", None),
    ("change the tax level for food", 24, "single", None),
    # ---- Q25 product codes ----
    ("add multiple product codes to a product", 25, "single", None),
    ("give a product an EAN barcode", 25, "single", None),
    # ---- merges (multi-intent) ----
    ("add a burger and only show it during lunch", 1, "merge", [1, 17]),
    ("add apple juice as a drink on the lunch menu with allergens", 1, "merge", [1, 6, 17]),
    ("make a fixed price menu only available during lunch", 16, "merge", [16, 17]),
    # ---- ambiguous / no-match ----
    ("change the price of my coffee", None, "clarify", None),
    ("how is the weather today", None, "none", None),
]


def run():
    log = []
    def w(s=""):
        log.append(s); print(s)
    w("=" * 72)
    w("CHATBOT END-TO-END SMOKE TEST  (POST /api/chat, %d questions)" % len(TESTS))
    w("=" * 72)
    npass = 0; fails = []
    for i, (q, exp, act, gexp) in enumerate(TESTS, 1):
        try:
            r = client.post("/api/chat", json={"message": q, "polish": False})
            d = r.get_json() or {}
        except Exception as e:
            d = {"_error": str(e)}
        qid = d.get("qid")
        action = d.get("action")
        guides = d.get("guides")
        ans = (d.get("answer") or "").replace("\n", " ")
        # decide pass
        if act == "none":
            good = qid in (None, "", 0)
        elif act == "clarify":
            good = action == "clarify"
        else:  # single / merge
            good = (action == act) and (exp is None or qid == exp) \
                   and (gexp is None or guides == gexp)
        npass += good
        flag = "PASS" if good else "FAIL"
        if not good:
            fails.append((i, q, exp, act, gexp, qid, action, guides))
        w("")
        w("[%02d] %s  | exp Q%s/%s%s" % (i, flag, exp, act,
            (" guides=%s" % gexp) if gexp else ""))
        w("     Q: %s" % q)
        w("     -> action=%s qid=%s guides=%s" % (action, qid, guides))
        w("     ans: %s" % (ans[:160] + ("..." if len(ans) > 160 else "")))
    w("")
    w("=" * 72)
    w("RESULT: %d/%d passed" % (npass, len(TESTS)))
    if fails:
        w("\nFAILURES:")
        for i, q, exp, act, gexp, qid, action, guides in fails:
            w("  [%02d] '%s'" % (i, q))
            w("       expected Q%s/%s%s  got Q%s/%s guides=%s"
              % (exp, act, (" g=%s" % gexp) if gexp else "", qid, action, guides))
    w("=" * 72)
    out = ROOT / "output" / "chat_smoketest_results.txt"
    out.write_text("\n".join(log), encoding="utf-8")
    print("\nSaved transcript -> %s" % out)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(run())
