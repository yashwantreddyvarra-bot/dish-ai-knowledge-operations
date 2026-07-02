"""
test_modeB.py - 10 random questions (5 easy + 5 hard) through the EXACT chatbot mode-B flow:
the question is parsed for the product (same as the chatbot), the guide is BUILT LIVE with
that product, and the name-entry frame is saved as a proof image so we can confirm the
product the user asked for is the one shown (not a sample).
"""
import sys, shutil, re, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from intelligence import agent
from capture import engine
from generate import doc_generator

QUESTIONS = [
    ("easy", "add a green tea as a drink for 2.5"),
    ("easy", "add a chicken caesar wrap as a food"),
    ("easy", "add an orange juice to the menu"),
    ("easy", "create a new espresso product for 2"),
    ("easy", "add a chocolate brownie as a dessert"),
    ("hard", "add a margarita pizza for 11 and only show it at lunch"),
    ("hard", "add a craft lager, list its allergens, and put it on the menu"),
    ("hard", "add a quinoa salad and give it a barcode"),
    ("hard", "register a strawberry milkshake priced 5.5 with a plu"),
    ("hard", "I want to add a veggie spring roll as a starter and assign it to the lunch menu"),
]


def run():
    out = []
    def w(s=""):
        out.append(s); print(s, flush=True)
    w("=" * 80)
    w("MODE B - 10 questions, build live, prove the asked product is what shows")
    w("=" * 80)
    for i, (lvl, q) in enumerate(QUESTIONS, 1):
        pl = agent.answer(q, polish=False)
        qid = pl.get("qid"); params = pl.get("params", {})
        name = params.get("product_name"); price = params.get("price")
        w("\n[%02d/%s] %s" % (i, lvl, q))
        w("     parsed -> name=%r price=%r -> guide Q%s (%s)" % (name, price, qid, pl.get("action")))
        if not (qid and name):
            w("     (no product to build)"); continue
        try:
            engine.main(qid=qid, headless=False, extra_vars={"NAME": name, "PRICE": price or "5.00"})
            doc_generator.build(qid)
            src = ROOT / "output" / "vframes" / ("q%02d" % qid) / "step_05.png"
            if src.exists():
                dst = ROOT / "output" / ("proofB_%02d_%s.png" % (i, re.sub(r"[^A-Za-z0-9]+", "_", name)))
                shutil.copy(src, dst)
                w("     PROOF -> %s" % dst.name)
        except Exception as e:
            w("     build failed: %s" % str(e)[:100])
    w("\n" + "=" * 80)
    w("Done. Proof images output/proofB_*.png - each should show its product in the Name field.")
    (ROOT / "output" / "test_modeB_results.txt").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    run()
