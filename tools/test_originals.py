"""
test_originals.py - the canonical ORIGINAL 25 questions (one per guide, the official
task title phrased as a question). Posts each to the chatbot, checks routing, and reports
the PDF / Video / Steps / overall score for the guide it lands on.
"""
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import server  # noqa
client = server.app.test_client()


def quality(qid):
    try:
        d = json.loads((ROOT / "output" / ("verify_q%02d.json" % qid)).read_text(encoding="utf-8"))
        return d.get("score"), d.get("pdf_score"), d.get("video_score"), d.get("steps_score")
    except Exception:
        return None, None, None, None


def run():
    qs = json.loads((ROOT / "questions.json").read_text(encoding="utf-8"))["questions"]
    log = []
    def w(s=""):
        log.append(s); print(s, flush=True)
    w("=" * 78)
    w("ORIGINAL 25 QUESTIONS  (one per guide) - routing + PDF/Video/Steps scores")
    w("=" * 78)
    ok = 0; ov = []; pf = []; vd = []; sp = []
    for q in qs:
        qid = q["id"]; title = q["title"]
        msg = "How do I %s?" % (title[0].lower() + title[1:])
        try:
            d = client.post("/api/chat", json={"message": msg, "polish": False}).get_json() or {}
        except Exception as e:
            d = {"_error": str(e)}
        got = d.get("qid")
        routed = (got == qid)
        ok += routed
        o, p, v, s = quality(qid)
        if o is not None:
            ov.append(o); pf.append(p); vd.append(v); sp.append(s)
        w("Q%-2d %s | route=%s | overall=%s PDF=%s Video=%s Steps=%s | %s"
          % (qid, "OK " if routed else "MIS", got, o, p, v, s, title[:40]))
    w("")
    w("=" * 78)
    w("ROUTING: %d/25 correct" % ok)
    if ov:
        w("DOC QUALITY (all 25): overall %.1f | PDF %.1f | Video %.1f | Steps %.1f"
          % (sum(ov)/len(ov), sum(pf)/len(pf), sum(vd)/len(vd), sum(sp)/len(sp)))
        w("   guides >=90 overall: %d/25" % sum(1 for x in ov if x >= 90))
        w("   guides >=90 on PDF:  %d/25" % sum(1 for x in pf if x >= 90))
        w("   guides >=90 on Steps:%d/25" % sum(1 for x in sp if x >= 90))
    w("=" * 78)
    (ROOT / "output" / "test_originals_results.txt").write_text("\n".join(log), encoding="utf-8")
    print("\nSaved -> output/test_originals_results.txt")


if __name__ == "__main__":
    run()
