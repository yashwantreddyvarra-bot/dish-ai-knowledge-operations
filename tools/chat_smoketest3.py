"""
chat_smoketest3.py - 100-QUESTION GENERALIZATION + QUALITY test.

4 freshly-worded questions per guide (Q1..Q25). For each it asks the REAL chatbot
(/api/chat -> phrase agent, then GPT semantic fallback for anything unrecognised) and records:
  - did it route to the right guide? (understanding)
  - what /100 quality score does that guide carry? (the score the user actually experiences)

Reports routing accuracy, the score distribution, % of questions that land on a >=90 doc,
and every mis-route / low-score landing. This is the honest "is the whole thing ready" metric.
"""
import sys, glob, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import server  # noqa
client = server.app.test_client()

# 4 varied phrasings per guide -> (question, expected_qid)
Q = {
 1:["add a new latte to the menu","create a product called veggie wrap",
    "I want to put a new cocktail on the drinks menu","register a new dessert item for 4.50"],
 2:["edit several products at once","change product names in the list view",
    "bulk edit my products","quick inline edit in the overview list"],
 3:["add a sales restriction to a product","restrict an item so only adults can buy it",
    "set a restriction on when an item is sold","assign sales restrictions to a dish"],
 4:["create a combo meal","bundle a burger and fries together",
    "make a composite product","build a meal deal from several items"],
 5:["search for a product","how do I filter my products",
    "find an item quickly in the list","use the search and filter function"],
 6:["add allergens to a product","mark gluten on my pizza",
    "tag additives on a dish","note the allergy info for an item"],
 7:["adjust a product's details","edit product information",
    "update an existing product","change the details of a product"],
 8:["enable regime forfettario","turn on the italian flat-rate tax",
    "activate the forfettario scheme","set up simplified italian tax"],
 9:["set the production order","configure the kitchen prep order",
    "change the order items are prepared in","set the production sequence"],
 10:["manage all my products","how do I manage products",
     "open product management","manage and add products"],
 11:["assign a plu number","set a price look-up code on an item",
     "add a plu to a product","configure plu numbers"],
 12:["create a new product group","add a category for drinks",
     "make a new product group for desserts","add a new group"],
 13:["create a price set","add a pricing rule",
     "set up a price set","configure a pricing rule set"],
 14:["add a price level","create a new price level",
     "set up a takeaway price level","manage my price levels"],
 15:["create a derived menu","make a child menu from a base menu",
     "set up a menu derived from another","build a derived menu"],
 16:["create a french menu","set up a fixed price menu",
     "make a 3 course prix fixe menu","build a set-price menu"],
 17:["add a time period","create a lunch time period",
     "make a menu show only during dinner","set time restrictions on a menu"],
 18:["create a promotion","set up a happy hour discount",
     "add a special offer","make a discount promo"],
 19:["arrange my menu","add a submenu to my menu",
     "reorganise my menu structure","manage my menus with submenus"],
 20:["assign a price level to a store","set a store price level",
     "apply a price level to my downtown store","link a price level to a store"],
 21:["turn off ticket printing","disable automatic kitchen tickets",
     "stop tickets printing automatically","I don't want tickets to print automatically"],
 22:["assign a menu to a specific area","set which menu shows in the bar area",
     "a menu for a specific area and time","assign menu to area for a facility"],
 23:["add a packaging profile","set up a takeaway packaging deposit",
     "create a packaging deposit profile","configure a container deposit"],
 24:["change the vat for food","set the tax level for food products",
     "lower the vat rate on food items","change food vat"],
 25:["add product codes to an item","give a product a barcode",
     "register an EAN code for a product","add multiple codes to a product"],
}


def doc_quality(qid):
    f = ROOT / "output" / ("verify_q%02d.json" % qid)
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        return d.get("score"), d.get("pdf_score"), d.get("video_score"), d.get("steps_score")
    except Exception:
        return None, None, None, None


def doc_score(qid):
    return doc_quality(qid)[0]


def run():
    log = []
    def w(s=""):
        log.append(s); print(s, flush=True)
    tests = [(q, qid) for qid, lst in Q.items() for q in lst]
    w("=" * 76)
    w("100-QUESTION GENERALIZATION + QUALITY TEST  (%d questions, all 25 guides)" % len(tests))
    w("=" * 76)
    route_ok = 0; misroutes = []; scored = []; pdfs = []; vids = []; stps = []; n = 0
    for q, exp in tests:
        n += 1
        try:
            d = client.post("/api/chat", json={"message": q, "polish": False}).get_json() or {}
        except Exception as e:
            d = {"_error": str(e)}
        qid = d.get("qid")
        ok = (qid == exp)
        route_ok += ok
        sc, pf, vd, sp = doc_quality(qid) if qid else (None, None, None, None)
        if sc is not None:
            scored.append(sc)
            if pf is not None: pdfs.append(pf)
            if vd is not None: vids.append(vd)
            if sp is not None: stps.append(sp)
        if not ok:
            misroutes.append((q, exp, qid))
        flag = "ok " if ok else "MIS"
        w("[%03d] %s exp Q%-2d got Q%-4s score=%s | %s"
          % (n, flag, exp, qid if qid else "none", sc if sc is not None else "-", q[:48]))
    w("")
    w("=" * 76)
    acc = 100.0 * route_ok / len(tests)
    w("ROUTING: %d/%d correct (%.0f%%)" % (route_ok, len(tests), acc))
    if scored:
        avg = sum(scored) / len(scored)
        ge90 = sum(1 for s in scored if s >= 90)
        ge80 = sum(1 for s in scored if s >= 80)
        lt80 = sorted(set(s for s in scored if s < 80))
        w("EXPERIENCED DOC QUALITY across the %d routed answers:" % len(scored))
        w("   overall average = %.1f/100" % avg)
        if pdfs: w("   PDF   average = %.1f/100" % (sum(pdfs)/len(pdfs)))
        if vids: w("   Video average = %.1f/100" % (sum(vids)/len(vids)))
        if stps: w("   Steps average = %.1f/100" % (sum(stps)/len(stps)))
        w("   %d/%d (%.0f%%) land on a guide scoring >=90" % (ge90, len(scored), 100.0*ge90/len(scored)))
        w("   %d/%d (%.0f%%) land on a guide scoring >=80" % (ge80, len(scored), 100.0*ge80/len(scored)))
    if misroutes:
        w("\nMIS-ROUTES (%d):" % len(misroutes))
        for q, exp, got in misroutes:
            w("   '%s'  exp Q%d got Q%s" % (q, exp, got))
    w("=" * 76)
    (ROOT / "output" / "test100_results.txt").write_text("\n".join(log), encoding="utf-8")
    print("\nSaved -> output/test100_results.txt")
    return 0


if __name__ == "__main__":
    sys.exit(run())
