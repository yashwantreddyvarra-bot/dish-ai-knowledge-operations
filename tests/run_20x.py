"""
run_20x.py - runs the agent brain's full assertion set 20 times and prints a
verdict. Lets us prove on THIS machine that routing/extraction/merge are correct
and deterministic. No network or model key required.

Run in PyCharm:  right-click -> Run 'run_20x'   (or the green arrow)
Or terminal:     python tests/run_20x.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from intelligence import agent


def run_once():
    fails = []

    def ck(name, cond, detail=""):
        if not cond:
            fails.append("%s  %s" % (name, detail))

    # --- parameter extraction (the "smartness") ---
    p = agent.extract_params("I want to add apple juice cocktail as a drink and bring it to the menu")
    ck("name", p["product_name"] == "Apple Juice Cocktail", p["product_name"])
    ck("type", p["type"] == "drink", p["type"])
    ck("price-auto", p["price"] and p["price_auto"], str(p))
    ck("cat", p["category_pref"][0] == "Soft Drinks", str(p["category_pref"]))
    ck("is_add", p["is_add"], str(p["is_add"]))
    p = agent.extract_params("add a burger for 8.50")
    ck("burger", p["product_name"] == "Burger", p["product_name"])
    ck("food", p["type"] == "food", p["type"])
    ck("price-given", p["price"] == "8.50" and not p["price_auto"], str(p))
    p = agent.extract_params("create a product called Espresso Martini priced at 9")
    ck("espresso martini", p["product_name"] == "Espresso Martini", p["product_name"])
    ck("price9", p["price"] == "9.00", p["price"])
    ck("martini-drink", p["type"] == "drink", p["type"])
    p = agent.extract_params("add green tea")
    ck("green tea", p["product_name"] == "Green Tea", p["product_name"])
    ck("auto350", p["price"] == "3.50" and p["price_auto"], str(p))
    ck("allergen-not-add", not agent.extract_params("add allergens to my pizza")["is_add"], "")

    # --- single routing (22 guides) ---
    singles = [
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
    for q, exp in singles:
        pl = agent.plan(q)
        ck("route:%s" % q[:28], pl["action"] in ("single", "merge") and pl.get("primary") == exp,
           "got %s %s" % (pl["action"], pl.get("guides")))

    # --- merge / clarify / none ---
    pl = agent.plan("add a burger and only show it during lunch")
    ck("merge 1+17", pl["action"] == "merge" and pl["guides"] == [1, 17], str(pl.get("guides")))
    pl = agent.plan("add apple juice cocktail as a drink, on the lunch menu, with allergens")
    ck("merge 1+6+17", pl["action"] == "merge" and pl["guides"] == [1, 6, 17], str(pl.get("guides")))
    pl = agent.plan("add apple juice cocktail as a drink and bring it to the menu")
    ck("single 1", pl["action"] == "single" and pl["guides"] == [1], str(pl.get("guides")))
    ck("clarify", agent.plan("how do I change a price")["action"] == "clarify", "")
    ck("none-taxes", agent.plan("how do I do my taxes")["action"] == "none", "")
    ck("none-weather", agent.plan("what is the weather today")["action"] == "none", "")

    # --- answer assembly uses the user's product + is grounded ---
    res = agent.answer("I want to add apple juice cocktail as a drink and bring it to the menu")
    ck("ans-name", "Apple Juice Cocktail" in res["answer"], "")
    ck("ans-vars", res["recipe_vars"].get("NAME") == "Apple Juice Cocktail", str(res.get("recipe_vars")))
    ck("ans-qid1", res["qid"] == 1, str(res["qid"]))
    res = agent.answer("add a burger and only show it during lunch")
    ck("merged-titles", "First" in res["answer"] and "Then" in res["answer"], "")
    ck("merged-2src", len(res["sources"]) == 2, str(res["sources"]))

    # --- messy / unseen phrasings ---
    messy = [
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
    ]
    for q, exp, act in messy:
        pl = agent.plan(q)
        ck("messy:%s" % q[:26], pl["action"] == act and (exp is None or pl.get("primary") == exp),
           "got %s %s" % (pl["action"], pl.get("primary")))

    return fails


def main():
    print("=" * 64)
    print("Running the agent brain assertion set 20 times on THIS machine")
    print("Python:", sys.version.split()[0])
    print("=" * 64)
    all_ok = True
    total_checks = 0
    for i in range(1, 21):
        fails = run_once()
        # count checks once
        if i == 1:
            # re-run count by length of a fresh pass is implicit; report fails only
            pass
        status = "PASS" if not fails else "FAIL (%d)" % len(fails)
        if fails:
            all_ok = False
        print("run %2d/20:  %s" % (i, status))
        for f in fails[:6]:
            print("            - %s" % f)
    print("=" * 64)
    print("FINAL:", "ALL 20 RUNS PASSED - OK" if all_ok else "SOME RUNS FAILED")
    print("=" * 64)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
