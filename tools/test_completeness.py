"""
test_completeness.py - runs many questions with the REAL GPT polish ON and checks that
every answer contains ALL the guide's steps (catches the truncation bug where long /
merged answers stopped early). Also reports routing.

Note: each guide's answer is the same regardless of how the question is worded, so these
~100 questions + the merges cover every completeness case (150 random would just repeat).
"""
import sys, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import server  # noqa
from tools.chat_smoketest3 import Q  # the 100 phrasings, 4 per guide
client = server.app.test_client()


def guide_steps(qid):
    try:
        d = json.loads((ROOT / "recipes" / ("Q%02d_script.json" % qid)).read_text(encoding="utf-8"))
        return len(d.get("steps", []))
    except Exception:
        return 0


def run():
    tests = [(q, qid) for qid, lst in Q.items() for q in lst]
    tests += [
        ("add a burger and only show it during lunch", 1),
        ("add apple juice as a drink on the lunch menu with allergens", 1),
        ("create a club sandwich and give it a barcode", 1),
    ]
    log = []
    def w(s=""):
        log.append(s); print(s, flush=True)
    w("=" * 78)
    w("COMPLETENESS TEST (polish ON) - %d questions; every answer must keep ALL steps" % len(tests))
    w("=" * 78)
    route_ok = 0; complete_ok = 0; incomplete = []; n = 0
    for q, exp in tests:
        n += 1
        try:
            d = client.post("/api/chat", json={"message": q, "polish": True}).get_json() or {}
        except Exception as e:
            d = {"_error": str(e)}
        qid = d.get("qid"); ans = d.get("answer") or ""
        nsteps = len(re.findall(r"(?m)^\s*\d+\.", ans))
        need = guide_steps(qid) if qid else 0
        route_ok += (qid == exp)
        complete = bool(qid and nsteps >= need and need > 0)
        complete_ok += complete
        if qid and need and nsteps < need:
            incomplete.append((q, qid, nsteps, need))
        if n % 10 == 0 or (qid and nsteps < need):
            w("[%03d] Q%-4s steps=%d/%d %s | %s"
              % (n, qid, nsteps, need, "" if complete else "<-- INCOMPLETE", q[:42]))
    w("")
    w("=" * 78)
    w("ROUTING: %d/%d correct" % (route_ok, len(tests)))
    w("COMPLETE ANSWERS: %d/%d kept all their steps" % (complete_ok, len(tests)))
    if incomplete:
        w("\nINCOMPLETE (truncated) ANSWERS:")
        for q, qid, got, need in incomplete:
            w("   Q%d  got %d/%d steps  | '%s'" % (qid, got, need, q))
    else:
        w("\nNo truncated answers - every guide returned its full step list.")
    w("=" * 78)
    (ROOT / "output" / "completeness_results.txt").write_text("\n".join(log), encoding="utf-8")
    print("\nSaved -> output/completeness_results.txt")


if __name__ == "__main__":
    run()
