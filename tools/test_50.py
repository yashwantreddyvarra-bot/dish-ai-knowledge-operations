"""
test_50.py - 50 random questions through the REAL chatbot server (server.app test_client,
exercises the full tier stack: follow-up memory -> phrase agent -> GPT). Checks routing +
action for each and prints PASS/FAIL with a failures list.

Entry: (question, expected_qid_or_None, expected_action, fresh)
  fresh=True  -> clears conversation memory first (a brand-new ask)
  fresh=False -> keeps memory (a follow-up that depends on the previous line)
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import server  # noqa
client = server.app.test_client()

T = [
    # --- coverage: one per guide, varied wording ---
    ("add a new smoothie to the menu", 1, "single", True),
    ("edit a bunch of products quickly in the list", 2, "single", True),
    ("set an age restriction on an item", 3, "single", True),
    ("create a combo meal of burger and fries", 4, "single", True),
    ("where is the product search and filter", 5, "single", True),
    ("mark allergens on my pizza", 6, "single", True),
    ("update an existing product's details", 7, "single", True),
    ("turn on the italian flat-rate tax", 8, "single", True),
    ("set the kitchen prep order", 9, "single", True),
    ("manage all my products", 10, "single", True),
    ("assign a plu number to a product", 11, "single", True),
    ("create a new product group for drinks", 12, "single", True),
    ("set up a pricing rule set", 13, "single", True),
    ("create a new price level", 14, "single", True),
    ("make a derived menu from a base menu", 15, "single", True),
    ("create a fixed price menu", 16, "single", True),
    ("add a lunch time period", 17, "single", True),
    ("set up a happy hour discount", 18, "single", True),
    ("arrange my menu into submenus", 19, "single", True),
    ("assign a price level to my store", 20, "single", True),
    ("stop tickets printing automatically", 21, "single", True),
    ("assign a menu to a specific area", 22, "single", True),
    ("set up a takeaway packaging deposit", 23, "single", True),
    ("change the vat for food items", 24, "single", True),
    ("add multiple product codes to a product", 25, "single", True),
    # --- tricky paraphrases (no obvious keywords -> GPT tier) ---
    ("the kitchen keeps printing paper for every order, make it stop", 21, "single", True),
    ("shoppers should be able to scan my item at the till", 25, "single", True),
    ("I want a meal that bundles a few items together", 4, "single", True),
    ("let customers know my dish contains nuts", 6, "single", True),
    ("create a separate takeaway price level", 14, "single", True),
    ("hide a product unless it is dinner time", 17, "single", True),
    ("give a discount during happy hour", 18, "single", True),
    ("the kitchen printer should not auto print", 21, "single", True),
    # --- merges (multi-intent) ---
    ("add a veggie burger for 9 and only show it at lunch", 1, "merge", True),
    ("create a club sandwich, mark its allergens, and put it on the menu", 1, "merge", True),
    ("add a cola and give it a barcode", 1, "merge", True),
    ("add a flat white with allergens and a plu", 1, "merge", True),
    # --- clarify (ambiguous price) ---
    ("I want to change how much something costs", None, "clarify", True),
    ("how do I change the price", None, "clarify", True),
    ("change what a product costs", None, "clarify", True),
    # --- no match ---
    ("what time does the restaurant open", None, "none", True),
    ("how do I reset my password", None, "none", True),
    ("tell me a joke", None, "none", True),
    # --- follow-up flows (memory) ---
    ("add a mango lassi as a drink", 1, "single", True),
    ("now only show it during dinner", 17, "single", False),
    ("add a caesar salad", 1, "single", True),
    ("also mark its allergens", 6, "single", False),
    ("create a new ipa beer", 1, "single", True),
    ("make it available only at lunch", 17, "single", False),
]


def run():
    log = []
    def w(s=""):
        log.append(s); print(s, flush=True)
    w("=" * 80)
    w("50 RANDOM QUESTIONS via the real chatbot server")
    w("=" * 80)
    npass = 0; fails = []
    for i, (q, exp, act, fresh) in enumerate(T, 1):
        if fresh:
            server.CHAT_MEMORY.clear()
        try:
            d = client.post("/api/chat", json={"message": q, "polish": False}).get_json() or {}
        except Exception as e:
            d = {"_error": str(e)}
        qid = d.get("qid"); action = d.get("action")
        if act == "none":
            ok = qid in (None, "", 0)
        elif act == "clarify":
            ok = action == "clarify"
        else:
            ok = (action == act) and (qid == exp)
        npass += ok
        flag = "ok " if ok else "FAIL"
        tag = "  (follow-up)" if not fresh else ""
        w("[%02d] %s exp Q%s/%-7s -> got Q%s/%-7s | %s%s"
          % (i, flag, exp, act, qid, action, q[:40], tag))
        if not ok:
            fails.append((i, q, exp, act, qid, action))
    w("")
    w("=" * 80)
    w("RESULT: %d/%d passed" % (npass, len(T)))
    if fails:
        w("\nFAILURES:")
        for i, q, exp, act, qid, action in fails:
            w("  [%02d] '%s'  exp Q%s/%s  got Q%s/%s" % (i, q, exp, act, qid, action))
    else:
        w("\nALL 50 PASSED.")
    w("=" * 80)
    (ROOT / "output" / "test50_results.txt").write_text("\n".join(log), encoding="utf-8")
    print("\nSaved -> output/test50_results.txt")


if __name__ == "__main__":
    run()
