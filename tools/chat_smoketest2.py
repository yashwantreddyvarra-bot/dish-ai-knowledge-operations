"""
chat_smoketest2.py - ROUND 2. 50 fresh, naturally-phrased questions through the real
chatbot endpoint. For each: checks routing (action/qid) AND that the routed guide has a
real PDF + MP4 on disk (so the answer the user gets actually links to working outputs).
Also reports whether the OpenAI key works.

Run:  python -m tools.chat_smoketest2
Output: output/chat_smoketest2_results.txt
"""
import sys, glob
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import server  # noqa
from config.settings import DOCS_DIR, VIDEO_DIR

client = server.app.test_client()

# (question, expected_primary_qid_or_None, expected_action)
TESTS = [
    ("how do I create a new menu item for a smoothie", 1, "single"),
    ("I need to add a margherita pizza and show it on the menu", 1, "single"),
    ("set up a new cappuccino product", 1, "single"),
    ("add a new beer called Heineken for 5 euros", 1, "single"),
    ("I want to quickly edit a bunch of products in the list", 2, "single"),
    ("how to change product names directly in the overview list", 2, "single"),
    ("set an age restriction on a product", 3, "single"),
    ("add a sales restriction to an item", 3, "single"),
    ("I want to sell a meal deal with a main and a side", 4, "single"),
    ("combine several products into one combo", 4, "single"),
    ("where is the product search and filter", 5, "single"),
    ("I can't find a product, how do I search for it", 5, "single"),
    ("mark which allergens my dish contains", 6, "single"),
    ("how do I note that a meal contains nuts and gluten", 6, "single"),
    ("I need to update the details of an existing product", 7, "single"),
    ("edit a product's information", 7, "single"),
    ("activate the flat-rate tax scheme for italy", 8, "single"),
    ("configure the production order for the kitchen", 9, "single"),
    ("how do I manage all my products", 10, "single"),
    ("set a price look-up number on an item", 11, "single"),
    ("I want to create a new product group for drinks", 12, "single"),
    ("add a new category for sides", 12, "single"),
    ("set up a pricing rule set", 13, "single"),
    ("create a new price level", 14, "single"),
    ("create a child menu derived from a base menu", 15, "single"),
    ("set up a 3 course set menu at a fixed price", 16, "single"),
    ("create a french menu", 16, "single"),
    ("add a lunch time period", 17, "single"),
    ("make a menu show only during dinner", 17, "single"),
    ("create a discount offer", 18, "single"),
    ("set up a happy hour promotion", 18, "single"),
    ("reorganise my menu structure", 19, "single"),
    ("add a submenu to my menu", 19, "single"),
    ("apply a price level to one of my stores", 20, "single"),
    ("turn off automatic kitchen ticket printing", 21, "single"),
    ("I don't want tickets to print automatically", 21, "single"),
    ("assign a menu to a specific area", 22, "single"),
    ("set up a packaging deposit for takeaway", 23, "single"),
    ("add a packaging profile", 23, "single"),
    ("change the vat rate for food items", 24, "single"),
    ("set a different tax level for food", 24, "single"),
    ("add several barcodes to one product", 25, "single"),
    ("register an EAN code for an item", 25, "single"),
    # merges
    ("add a mojito as a drink and only show it during dinner", 1, "merge"),
    ("create a burger, list its allergens, and put it on the lunch menu", 1, "merge"),
    ("add a salad and give it a barcode", 1, "merge"),
    # ambiguous / no-match
    ("how do I change the price", None, "clarify"),
    ("what time does the restaurant open", None, "none"),
    ("how do I reset my password", None, "none"),
    ("tell me a joke", None, "none"),
]


def pdf_for(qid):
    return sorted(glob.glob(str(Path(DOCS_DIR) / ("Q%02d_branded_*.pdf" % qid))))


def mp4_for(qid):
    p = Path(VIDEO_DIR) / ("Q%02d_walkthrough.mp4" % qid)
    return p if p.exists() else None


def llm_status():
    try:
        from intelligence import llm
        if not llm.available():
            return "LLM: no key configured (deterministic only)"
        r = llm.ask_text("Reply with exactly: OK")
        if r and "ok" in r.lower():
            return "LLM: OK (OpenAI key works)"
        return "LLM: configured but no/odd reply -> %r" % (r,)
    except Exception as e:
        return "LLM: ERROR -> %s" % str(e)[:120]


def run():
    log = []
    def w(s=""):
        log.append(s); print(s)
    w("=" * 74)
    w("CHATBOT ROUND 2  (POST /api/chat, %d questions + PDF/video checks)" % len(TESTS))
    w(llm_status())
    w("=" * 74)
    npass = 0; fails = []
    for i, (q, exp, act) in enumerate(TESTS, 1):
        try:
            d = client.post("/api/chat", json={"message": q, "polish": False}).get_json() or {}
        except Exception as e:
            d = {"_error": str(e)}
        qid = d.get("qid"); action = d.get("action"); guides = d.get("guides")
        ans = (d.get("answer") or "").replace("\n", " ")
        # routing check
        if act == "none":
            route_ok = qid in (None, "", 0)
        elif act == "clarify":
            route_ok = action == "clarify"
        else:
            route_ok = (action == act) and (exp is None or qid == exp)
        # output (pdf/video) check - only for routed answers
        out_ok = True; out_note = ""
        if act in ("single", "merge") and qid:
            pdfs = pdf_for(qid); mp4 = mp4_for(qid)
            out_ok = bool(pdfs) and bool(mp4)
            out_note = "pdf=%s video=%s" % (
                Path(pdfs[-1]).name if pdfs else "MISSING",
                mp4.name if mp4 else "MISSING")
        good = route_ok and out_ok
        npass += good
        if not good:
            fails.append((i, q, exp, act, qid, action, guides, out_note, route_ok, out_ok))
        w("")
        w("[%02d] %s | exp Q%s/%s -> got Q%s/%s %s"
          % (i, "PASS" if good else "FAIL", exp, act, qid, action,
             ("guides=%s" % guides) if guides else ""))
        w("     Q: %s" % q)
        if out_note:
            w("     outputs: %s  (%s)" % (out_note, "ok" if out_ok else "PROBLEM"))
        w("     ans: %s" % (ans[:150] + ("..." if len(ans) > 150 else "")))
    w("")
    w("=" * 74)
    w("RESULT: %d/%d passed" % (npass, len(TESTS)))
    if fails:
        w("\nFAILURES:")
        for i, q, exp, act, qid, action, guides, out_note, r_ok, o_ok in fails:
            why = []
            if not r_ok: why.append("ROUTING")
            if not o_ok: why.append("OUTPUT(%s)" % out_note)
            w("  [%02d] '%s'  -> %s" % (i, q, ", ".join(why)))
            w("       expected Q%s/%s  got Q%s/%s guides=%s" % (exp, act, qid, action, guides))
    w("=" * 74)
    out = ROOT / "output" / "chat_smoketest2_results.txt"
    out.write_text("\n".join(log), encoding="utf-8")
    print("\nSaved -> %s" % out)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(run())
