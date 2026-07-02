"""promote.py - PROMOTION.

When a brand-new (live-agent) run passes the CONFIDENCE GATE, save it into the recipe
library so the question graduates from the typed lane into the trusted dropdown lane.
Writes a capture recipe + a caption script and registers the question in questions.json.
Only ever promotes a run the gate marked 'publish' (never an unsure one)."""
import json, glob, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REC = ROOT / "recipes"
QFILE = ROOT / "questions.json"


def _next_qid():
    ids = []
    for fp in glob.glob(str(REC / "Q*_capture.json")):
        m = re.search(r"Q0*(\d+)_capture", fp)
        if m:
            ids.append(int(m.group(1)))
    return (max(ids) + 1) if ids else 1


def promote(title, section, actions, captions, gate_result):
    """Persist a passed live run as a new recipe + dropdown entry. Returns the new qid,
    or None when the gate did not clear it (unsure runs are never auto-promoted)."""
    if not gate_result or gate_result.get("decision") != "publish":
        print("PROMOTE: skipped - gate did not publish (%s)" %
              (gate_result or {}).get("reason", "no gate"))
        return None
    qid = _next_qid()
    cap = {"qid": qid, "title": title, "workflow_title": title, "vars": {}, "actions": actions}
    (REC / ("Q%02d_capture.json" % qid)).write_text(json.dumps(cap, indent=2), encoding="utf-8")
    steps = [{"step": i + 1, "caption": c} for i, c in enumerate(captions)]
    scr = {"id": qid, "title": title, "workflow_title": title, "steps": steps}
    (REC / ("Q%02d_script.json" % qid)).write_text(json.dumps(scr, indent=2), encoding="utf-8")
    try:
        data = json.loads(QFILE.read_text(encoding="utf-8"))
        qs = data if isinstance(data, list) else data.get("questions", [])
        qs.append({"id": qid, "title": title, "section": section or "Products", "status": "ready"})
        if isinstance(data, list):
            QFILE.write_text(json.dumps(qs, indent=2), encoding="utf-8")
        else:
            data["questions"] = qs
            QFILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        print("PROMOTE: questions.json update failed:", e)
    print("PROMOTED: Q%02d '%s' added to the recipe library / dropdown" % (qid, title))
    return qid
