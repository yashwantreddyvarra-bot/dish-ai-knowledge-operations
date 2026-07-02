"""
improve.py - close the loop SAFELY: verify -> if weak, back up the build, re-capture
(model picks real controls, self-checks each pick) -> re-build -> re-verify. Keep the new
build ONLY if its score is higher; otherwise revert to the backup.

This makes auto-improvement *monotonic*: a question can get better or stay the same, never
worse. (Earlier, an unguarded re-capture regressed Q5/Q8 - this prevents that.)
"""
import sys, shutil
from pathlib import Path
from . import verify, llm

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
DOCS = OUT / "docs"
VID = OUT / "videos"
BK = OUT / "_backup"


def _backup(qid):
    d = BK / ("q%02d" % qid)
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
    (d / "docs").mkdir(parents=True, exist_ok=True)
    (d / "vframes").mkdir(parents=True, exist_ok=True)
    for p in DOCS.glob("Q%02d_branded_*.pdf" % qid):
        shutil.copy2(p, d / "docs" / p.name)
    mp4 = VID / ("Q%02d_walkthrough.mp4" % qid)
    if mp4.exists():
        shutil.copy2(mp4, d / mp4.name)
    for name in ("manifest_q%02d.json" % qid, "manifest_q%02d_enriched.json" % qid):
        if (OUT / name).exists():
            shutil.copy2(OUT / name, d / name)
    vf = OUT / "vframes" / ("q%02d" % qid)
    if vf.exists():
        for f in vf.glob("*.png"):
            shutil.copy2(f, d / "vframes" / f.name)
    return d


def _restore(qid, d):
    # remove the (worse) new PDF(s), put the backup build back
    for p in DOCS.glob("Q%02d_branded_*.pdf" % qid):
        try: p.unlink()
        except Exception: pass
    for p in (d / "docs").glob("*.pdf"):
        shutil.copy2(p, DOCS / p.name)
    for p in d.glob("Q%02d_walkthrough.mp4" % qid):
        shutil.copy2(p, VID / p.name)
    for name in ("manifest_q%02d.json" % qid, "manifest_q%02d_enriched.json" % qid):
        if (d / name).exists():
            shutil.copy2(d / name, OUT / name)
    vf = OUT / "vframes" / ("q%02d" % qid)
    vf.mkdir(parents=True, exist_ok=True)
    for f in (d / "vframes").glob("*.png"):
        shutil.copy2(f, vf / f.name)


def one(qid, target=90):
    before = verify.question(qid, use_vision=llm.available())
    sb = before.get("score", 0)
    print("Q%02d before: %d/100" % (qid, sb))
    if sb >= target and before.get("fail", 0) == 0:
        print("Q%02d already good, skipping." % qid); return before
    bk = _backup(qid)
    try:
        from capture import engine
        engine.main(qid=qid, headless=False)
        from generate import doc_generator
        doc_generator.build(qid)
    except Exception as e:
        print("re-capture/build failed (%s); restoring backup." % str(e)[:80])
        _restore(qid, bk); return before
    after = verify.question(qid, use_vision=llm.available())
    sa = after.get("score", 0)
    if sa > sb:
        print("Q%02d KEPT: %d/100  (was %d)  ✓ better" % (qid, sa, sb))
        return after
    else:
        print("Q%02d REVERTED: re-capture scored %d <= %d, restoring previous build." % (qid, sa, sb))
        _restore(qid, bk)
        return before


def run(qids, target=90):
    if not llm.available():
        print("NOTE: no model configured - vision off; re-runs use heuristics only.")
    results = []
    for q in qids:
        print("=" * 56)
        results.append(one(q, target))
    print("=" * 56)
    for r in results:
        print("Q%02d -> %d/100" % (r["qid"], r.get("score", 0)))
    return results


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        qids = list(range(1, 11))
    elif "-" in args[0]:
        a, b = args[0].split("-"); qids = list(range(int(a), int(b) + 1))
    else:
        qids = [int(x) for x in args]
    run(qids)
