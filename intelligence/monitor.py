"""
monitor.py - detect UI drift so the docs stay current on their own.

Keeps a baseline of each question's frames. On a re-run it compares the new frames to the
baseline; if a step's screenshot changed beyond a threshold, DISH likely changed that screen
and the tutorial should be rebuilt. Schedule check_all() nightly and it flags drift with zero
manual work. (Pairs with feedback.flagged() to decide what to rebuild.)
"""
import json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
BASE = OUT / "baselines"


def _phash(path):
    from PIL import Image, ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    im = Image.open(path).convert("L").resize((16, 16))
    px = list(im.getdata()); avg = sum(px) / len(px)
    return [1 if p > avg else 0 for p in px]


def _dist(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def snapshot_baseline(qid):
    """Save the current frames as the trusted baseline for this question."""
    src = OUT / "vframes" / ("q%02d" % qid)
    dst = BASE / ("q%02d" % qid)
    if not src.exists():
        return 0
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in src.glob("step_*.png"):
        try:
            shutil.copy2(f, dst / f.name); n += 1
        except Exception:
            pass
    return n


def check(qid, threshold=40):
    """Compare current frames to baseline. Returns drifted step numbers."""
    cur = OUT / "vframes" / ("q%02d" % qid)
    base = BASE / ("q%02d" % qid)
    if not base.exists():
        return {"qid": qid, "baseline": False, "drifted": []}
    drift = []
    for f in sorted(cur.glob("step_*.png")):
        b = base / f.name
        if not b.exists():
            drift.append(int(f.stem.split("_")[1])); continue
        try:
            if _dist(_phash(f), _phash(b)) > threshold:
                drift.append(int(f.stem.split("_")[1]))
        except Exception:
            pass
    return {"qid": qid, "baseline": True, "drifted": drift,
            "status": "DRIFT" if drift else "stable"}


def check_all(threshold=40):
    out = []
    for d in sorted((OUT / "vframes").glob("q*")):
        try:
            out.append(check(int(d.name[1:]), threshold))
        except Exception:
            pass
    flagged = [r for r in out if r.get("drifted")]
    print("monitor: %d questions checked, %d drifted" % (len(out), len(flagged)))
    for r in flagged:
        print("   Q%02d DRIFT at steps %s" % (r["qid"], r["drifted"]))
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == "baseline":
        print("baselined", snapshot_baseline(int(sys.argv[2])), "frames")
    else:
        check_all()
