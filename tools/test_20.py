"""
test_20.py - 20 random questions, fully checked per question:
  - routes the question (agent)
  - if it names a product, BUILDS the guide live with that product (no hardcoding)
  - verifies the resulting guide: Steps (instructions), PDF (screenshots+boxes), Video
Logs a per-question line + a list of anything defective so it can be fixed.
"""
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from intelligence import agent, verify

QUESTIONS = [
    # 4 product-add questions -> live tailored build (tests name + steps + ss + video)
    "add a mango lassi as a drink",
    "add a club sandwich for 8.50",
    "create a new espresso product",
    "put a caesar salad on the menu",
    # 16 varied questions -> existing guides
    "stop tickets printing automatically",
    "add allergens to my pizza",
    "set up a happy hour discount",
    "assign a plu number to a product",
    "create a new product group for desserts",
    "change the vat for food items",
    "make a fixed price menu",
    "arrange my menu into submenus",
    "add multiple product codes to a product",
    "set the production order for the kitchen",
    "edit several products in the list",
    "restrict a product so only adults can buy it",
    "search and filter my products",
    "set up a takeaway packaging deposit",
    "assign a price level to my store",
    "add a lunch time period",
]


def run():
    log = []
    def w(s=""):
        log.append(s); print(s, flush=True)
    w("=" * 80)
    w("20-QUESTION FULL CHECK  (Steps + PDF screenshots + Video, per question)")
    w("=" * 80)
    rows = []
    for i, q in enumerate(QUESTIONS, 1):
        pl = agent.answer(q, polish=False)
        qid = pl.get("qid"); params = pl.get("params", {})
        name = params.get("product_name")
        if not qid:
            w("\n[%02d] '%s' -> NO GUIDE" % (i, q)); continue
        # if a product is named, build the guide live with that product
        if name:
            w("\n[%02d] '%s' -> Q%d  | building live with product = %r ..." % (i, q, qid, name))
            try:
                from capture import engine
                engine.main(qid=qid, headless=False,
                            extra_vars={"NAME": name, "PRICE": params.get("price") or "5.00"})
                from generate import doc_generator
                doc_generator.build(qid)
            except Exception as e:
                w("     live build failed: %s" % str(e)[:90])
        else:
            w("\n[%02d] '%s' -> Q%d" % (i, q, qid))
        rep = verify.question(qid, use_vision=True)
        rows.append((i, q, qid, name, rep.get("pdf_score"), rep.get("video_score"),
                     rep.get("steps_score"), rep.get("score"), rep.get("fail"), rep.get("warn")))
        w("     STEPS=%s  PDF=%s  VIDEO=%s  overall=%s  (fail=%s warn=%s)"
          % (rep.get("steps_score"), rep.get("pdf_score"), rep.get("video_score"),
             rep.get("score"), rep.get("fail"), rep.get("warn")))
        for s in rep.get("steps", []):
            if s["status"] != "ok":
                w("        step %02d %s: %s" % (s["step"], s["status"].upper(), "; ".join(s["issues"])))

    w("\n" + "=" * 80)
    w("SUMMARY (per question)")
    for i, q, qid, name, pf, vd, st, ov, f, wn in rows:
        tag = (" name=%s" % name) if name else ""
        w("  [%02d] Q%-2d Steps=%-3s PDF=%-3s Video=%-3s overall=%-3s%s  | %s"
          % (i, qid, st, pf, vd, ov, tag, q[:34]))
    defective = [r for r in rows if (r[8] or 0) > 0]   # fail>0 = a wrong screenshot/box
    w("\n  NEEDS FIXING (wrong screenshot/box): %s"
      % (", ".join("Q%d" % r[2] for r in defective) if defective else "none"))
    if rows:
        w("  averages: Steps=%.0f  PDF=%.0f  Video=%.0f  overall=%.0f"
          % (sum(r[6] for r in rows)/len(rows), sum(r[4] for r in rows)/len(rows),
             sum(r[5] for r in rows)/len(rows), sum(r[7] for r in rows)/len(rows)))
    w("=" * 80)
    (ROOT / "output" / "test20_results.txt").write_text("\n".join(log), encoding="utf-8")
    print("\nSaved -> output/test20_results.txt")


if __name__ == "__main__":
    run()
