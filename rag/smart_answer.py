"""
smart_answer.py - GPT-powered intent understanding for the chatbot.

Turns a free-form / paraphrased user question ("how do I stop the kitchen ticket
printing?") into: the single best-matching guide (qid) + a concise, grounded answer
written ONLY from that guide's real captured steps. Falls back gracefully to None
so server.py can use the keyword retriever when no model key is set.
"""
import json, glob, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REC = ROOT / "recipes"


def _catalog():
    """All built guides: {qid, title, steps:[captions]} from the recipe scripts."""
    guides = []
    for fp in sorted(glob.glob(str(REC / "Q*_script.json"))):
        try:
            d = json.loads(Path(fp).read_text(encoding="utf-8"))
        except Exception:
            continue
        qid = d.get("id")
        if qid is None:
            m = re.search(r"Q0*(\d+)_script", fp)
            qid = int(m.group(1)) if m else None
        title = d.get("title") or d.get("workflow_title") or ("Question %s" % qid)
        steps = [s.get("caption", "").strip() for s in d.get("steps", []) if s.get("caption")]
        if qid is not None:
            guides.append({"qid": qid, "title": title, "steps": steps})
    return sorted(guides, key=lambda g: g["qid"])


def _catalog_text(guides, with_steps=True):
    out = []
    for g in guides:
        line = "[%d] %s" % (g["qid"], g["title"])
        if with_steps and g["steps"]:
            line += "\n    steps: " + " | ".join(g["steps"])
        out.append(line)
    return "\n".join(out)


SYSTEM = ("You are the DISH POS Backoffice documentation assistant for DISH Digital "
          "Solutions. You help restaurant staff by answering their questions using ONLY "
          "the official guides provided. Be concise, practical and accurate. Never invent "
          "steps that are not in the chosen guide.")


def answer(query, history=None, section=None):
    """Return {answer, qid, title, matched} using GPT, or None if no model available.
    `history` is a list of recent user messages (conversation memory) so the model can
    resolve follow-ups like 'now put it on the menu'.
    `section`, when given, restricts the model to guides in that one section so the
    answer never crosses into another section."""
    from intelligence import llm
    if not llm.available():
        return None
    guides = _catalog()
    if not guides:
        return None
    if section:
        try:
            from intelligence.agent import section_of
            scoped = [g for g in guides if section_of(g["qid"]) == section]
            if scoped:
                guides = scoped
        except Exception:
            pass
    ctx = ""
    if history:
        ctx = ("Earlier in this same chat the user said (oldest first): %s\n"
               "Use this to resolve references like 'it', 'that', 'the product'.\n\n"
               % " | ".join(history[-5:]))
    prompt = (
        ctx +
        "A user asked: \"%s\"\n\n"
        "Here are the available official guides (id, title, and their real steps):\n\n%s\n\n"
        "Pick the SINGLE guide that best answers the user's question. Then write a short, "
        "clear answer to their question using ONLY that guide's steps (you may condense or "
        "rephrase, but stay faithful). If the question is broad, summarise the key steps. "
        "If NO guide fits, set qid to null and briefly say you don't have a guide for that yet.\n\n"
        "Respond with STRICT JSON only, no markdown:\n"
        '{\"qid\": <number or null>, \"title\": \"<guide title or empty>\", \"answer\": \"<your answer>\"}'
    ) % (query, _catalog_text(guides))

    raw = llm.ask_text(prompt, system=SYSTEM, max_tokens=900)
    if not raw:
        return None
    # extract JSON (model sometimes wraps it)
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        data = json.loads(m.group(0) if m else raw)
    except Exception:
        # model gave prose - return it as a plain answer with no routing
        return {"answer": raw.strip(), "qid": None, "title": "", "matched": False}
    qid = data.get("qid")
    qid = int(qid) if isinstance(qid, (int, float)) or (isinstance(qid, str) and qid.isdigit()) else None
    # Safety net: never return a guide outside the requested section.
    if section and qid is not None:
        try:
            from intelligence.agent import section_of
            if section_of(qid) != section:
                qid = None
        except Exception:
            pass
    return {"answer": (data.get("answer") or "").strip(),
            "qid": qid, "title": data.get("title", ""), "matched": qid is not None}


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "how do I stop tickets printing automatically?"
    print(json.dumps(answer(q), indent=2))
