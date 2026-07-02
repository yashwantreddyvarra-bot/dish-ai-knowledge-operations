"""
test_50_content.py - asks 50 random questions through the real chatbot, and for the guide
each one generates, reports the CONTENT quality from the vision check that inspected every
screenshot: PDF (screenshots + boxes), Video (frames + boxes), Steps (captions vs screens).
"""
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import server  # noqa
from tools.test_50 import T   # reuse the 50 questions
client = server.app.test_client()


def scores(qid):
    try:
        d = json.loads((ROOT / "output" / ("verify_q%02d.json" % qid)).read_text(encoding="utf-8"))
        return d.get("pdf_score"), d.get("video_score"), d.get("steps_score")
    except Exception:
        return None, None, None


def run():
    log = []
    def w(s=""):
        log.append(s); print(s, flush=True)
    w("=" * 84)
    w("50 RANDOM QUESTIONS - content check (PDF / Video / Steps of the generated guide)")
    w("=" * 84)
    pdfs = []; vids = []; stps = []
    for i, (q, exp, act, fresh) in enumerate(T, 1):
        if fresh:
            server.CHAT_MEMORY.clear()
        d = client.post("/api/chat", json={"message": q, "polish": False}).get_json() or {}
        qid = d.get("qid")
        if not qid:
            w("[%02d] %-46s -> (clarify / no guide)" % (i, q[:46])); continue
        pf, vd, st = scores(qid)
        if pf is not None:
            pdfs.append(pf); vids.append(vd); stps.append(st)
        flag = "" if (pf and pf >= 90 and st and st >= 90) else "  <-- check"
        w("[%02d] %-44s -> Q%-2d  PDF=%-3s Video=%-3s Steps=%-3s%s"
          % (i, q[:44], qid, pf, vd, st, flag))
    w("")
    w("=" * 84)
    if pdfs:
        w("AVERAGES across the generated guides:  PDF=%.0f  Video=%.0f  Steps=%.0f"
          % (sum(pdfs)/len(pdfs), sum(vids)/len(vids), sum(stps)/len(stps)))
        w("  guides hit with PDF>=90:   %d/%d" % (sum(1 for x in pdfs if x >= 90), len(pdfs)))
        w("  guides hit with Steps>=90: %d/%d" % (sum(1 for x in stps if x >= 90), len(stps)))
    w("=" * 84)
    (ROOT / "output" / "test50_content.txt").write_text("\n".join(log), encoding="utf-8")
    print("\nSaved -> output/test50_content.txt")


if __name__ == "__main__":
    run()
