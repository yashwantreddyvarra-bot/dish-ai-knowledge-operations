# rag/simple_index.py - zero-dependency retriever spanning ALL built questions.
import json, math, re, glob
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
_WORD = re.compile(r"[a-z0-9]+")

def _tok(t): return _WORD.findall(t.lower())

def _load_steps():
    files = sorted(glob.glob(str(OUT / "manifest_q*_enriched.json")))
    if not files:
        legacy = OUT / "manifest_enriched.json"
        files = [str(legacy)] if legacy.exists() else []
    steps = []; last_wf = ""
    for fp in files:
        try:
            data = json.JSONDecoder().raw_decode(open(fp, encoding="utf-8").read())[0]
        except Exception:
            continue
        wf = data.get("workflow_title", data.get("product_name", "Workflow")); last_wf = wf
        for s in data.get("screenshots", []):
            cap = (s.get("llm_caption") or s.get("label", "")).replace("_", " ").strip()
            if cap:
                steps.append({"text": cap, "workflow": wf, "step": s.get("step")})
    return steps, last_wf

def _index(docs):
    toks = [_tok(d["text"]) for d in docs]
    df = Counter()
    for t in toks:
        for w in set(t): df[w] += 1
    n = len(docs) or 1
    idf = {w: math.log((n + 1) / (c + 1)) + 1 for w, c in df.items()}
    vecs = []
    for t in toks:
        tf = Counter(t)
        v = {w: (c / len(t)) * idf.get(w, 0) for w, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append((v, norm))
    return idf, vecs

def search(query, k=8):
    docs, wf = _load_steps()
    if not docs: return [], wf
    idf, vecs = _index(docs)
    qtf = Counter(_tok(query))
    if not qtf: return [], wf
    qv = {w: (c / len(qtf)) * idf.get(w, 0) for w, c in qtf.items()}
    qn = math.sqrt(sum(x * x for x in qv.values())) or 1.0
    scored = []
    for i, (dv, dn) in enumerate(vecs):
        dot = sum(v * dv.get(w, 0) for w, v in qv.items())
        scored.append((dot / (qn * dn) if qn and dn else 0.0, i))
    scored.sort(reverse=True)
    return [dict(docs[i], similarity=round(sc, 3)) for sc, i in scored[:k] if sc > 0], wf

def answer(query, k=8):
    hits, _ = search(query, k)
    if not hits:
        return {"answer": "I don't have captured steps matching that yet. Build a "
                "question and I'll answer from the real steps.", "sources": []}
    top = hits[0]["workflow"]
    same = sorted([h for h in hits if h["workflow"] == top], key=lambda h: h["step"] or 0)
    body = "\n".join("%s. %s" % (h["step"], h["text"]) for h in same)
    ans = "Here's how to %s:\n\n%s" % (top.lower(), body)
    src = [{"workflow": top, "steps": str(h["step"]), "similarity": h["similarity"]}
           for h in sorted(same, key=lambda h: -h["similarity"])[:3]]
    return {"answer": ans, "sources": src}

if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "How do I adjust a product price?"
    res = answer(q); print("Q:", q, "\n"); print(res["answer"]); print("\nsources:", res["sources"])
