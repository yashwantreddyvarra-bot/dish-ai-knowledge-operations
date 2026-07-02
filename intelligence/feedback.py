"""
feedback.py - LEARN: collect human feedback and turn it into improvement.

The chatbot exposes thumbs up/down per question (and per step). Ratings are stored here.
What the system does with them:

  - NEGATIVE ratings flag a question/step for automatic rebuild (flagged()).
  - POSITIVE ratings reinforce the selectors that produced that step in the resolver cache,
    so good strategies float to the top for every future question.
  - Over time this file IS your training set: page state + target + what worked + human
    rating. Point a fine-tune at output/feedback.json + output/resolver_cache.json when you
    have volume; that is the realistic "upgrade the neural network" step.
"""
import json, time
from pathlib import Path
from . import resolver

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "output" / "feedback.json"


def _load():
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:
        return {"events": []}


def _save(d):
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(d, indent=2), encoding="utf-8")


def record(qid, rating, step=None, note="", selector=None, target=None, url=""):
    """rating: 'up' or 'down'. Optionally tie to a step + the selector/target used."""
    d = _load()
    d["events"].append({"ts": int(time.time()), "qid": qid, "step": step,
                        "rating": rating, "note": note, "selector": selector,
                        "target": target, "url": url})
    _save(d)
    # reinforce good selectors immediately
    if rating == "up" and selector and target:
        resolver.record_success(target, selector, url)
    return {"ok": True, "total": len(d["events"])}


def summary():
    d = _load()
    per = {}
    for e in d["events"]:
        q = per.setdefault(e["qid"], {"up": 0, "down": 0})
        per[e["qid"]][e["rating"]] = per[e["qid"]].get(e["rating"], 0) + 1
    return {"total_events": len(d["events"]), "per_question": per}


def flagged():
    """Questions/steps with net-negative feedback that should be rebuilt."""
    d = _load()
    score = {}
    for e in d["events"]:
        key = (e["qid"], e.get("step"))
        score[key] = score.get(key, 0) + (1 if e["rating"] == "up" else -1)
    return [{"qid": q, "step": s, "net": v} for (q, s), v in score.items() if v < 0]


if __name__ == "__main__":
    print(json.dumps(summary(), indent=2))
    print("flagged:", flagged())
