"""
evaluate_docs.py - EVALUATE every generated document for CORRECTNESS, not just existence.

For each question Q1..Q25 it runs the vision verifier (verify.py): GPT-4o looks at every
captured frame and judges whether the orange highlight box is on the RIGHT element and the
screen matches the step caption. Produces:
  - a /100 quality score per document
  - the exact defective steps (wrong box / wrong screen / blank frame)
  - a scoreboard sorted worst-first so we know what to fix

Outputs: output/doc_evaluation.txt (human report) and output/doc_scores.json (qid -> score).
Run: python -m tools.evaluate_docs            (all 25)
     python -m tools.evaluate_docs 16 17 23   (subset)
"""
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from intelligence import verify, llm

OUT = ROOT / "output"


def run(qids):
    log = []
    def w(s=""):
        log.append(s); print(s, flush=True)
    w("=" * 74)
    w("DOCUMENT QUALITY EVALUATION  (vision /100 per guide)")
    w("LLM: %s" % ("OpenAI vision ON" if llm.available() else "NO KEY - heuristic only"))
    w("=" * 74)
    scores = {}
    rows = []
    for qid in qids:
        rep = verify.question(qid, use_vision=True)
        if "error" in rep:
            w("\nQ%02d  ERROR: %s" % (qid, rep["error"])); continue
        sc = rep["score"]; scores[qid] = sc
        defects = [s for s in rep["steps"] if s["status"] != "ok"]
        rows.append((qid, sc, rep["fail"], rep["warn"], len(rep["steps"])))
        w("\nQ%02d  overall=%d/100  | PDF %d  Video %d  Steps %d  (fail=%d warn=%d of %d)"
          % (qid, sc, rep.get("pdf_score", 0), rep.get("video_score", 0),
             rep.get("steps_score", 0), rep["fail"], rep["warn"], rep["total"]))
        for s in defects:
            tag = s["status"].upper()
            why = "; ".join(s["issues"]) or "; ".join(s["notes"])
            vis = (" | vision: " + s["vision"]) if s.get("vision") else ""
            w("     step %02d  %s  %s%s" % (s["step"], tag, why, vis))

    w("\n" + "=" * 74)
    w("SCOREBOARD (worst first)")
    for qid, sc, f, wn, tot in sorted(rows, key=lambda r: r[1]):
        bar = "#" * int(sc / 5)
        w("  Q%02d  %3d/100  %-20s fail=%d warn=%d" % (qid, sc, bar, f, wn))
    if rows:
        avg = sum(r[1] for r in rows) / len(rows)
        perfect = sum(1 for r in rows if r[2] == 0 and r[1] >= 90)
        clean = sum(1 for r in rows if r[2] == 0)
        w("\n  average=%.1f/100 | %d/%d have zero hard defects | %d/%d score >=90 with no fails"
          % (avg, clean, len(rows), perfect, len(rows)))
        worst = [r[0] for r in rows if r[2] > 0]
        if worst:
            w("  NEEDS FIXING (hard defects): " + ", ".join("Q%02d" % q for q in worst))
        else:
            w("  No hard defects anywhere.")
    w("=" * 74)
    (OUT / "doc_evaluation.txt").write_text("\n".join(log), encoding="utf-8")
    (OUT / "doc_scores.json").write_text(json.dumps(scores, indent=2), encoding="utf-8")
    print("\nSaved -> output/doc_evaluation.txt  and  output/doc_scores.json")


if __name__ == "__main__":
    args = [int(a) for a in sys.argv[1:]] or list(range(1, 26))
    run(args)
