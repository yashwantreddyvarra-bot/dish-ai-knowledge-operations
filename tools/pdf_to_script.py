# tools/pdf_to_script.py - turn an official iorad PDF into a correct QNN_script.json.
# Extracts the exact caption per page AND the orange-highlighted word (from PDF colors),
# so generated docs/answers always match DISH's official tutorial. Scales to all 25.
#
#   python tools/pdf_to_script.py <pdf> <qid> "<workflow_title>" [out.json]
import sys, json, re
from pathlib import Path
import pdfplumber

def _is_orange(c):
    col = c.get("non_stroking_color")
    if not col: return False
    try:
        if isinstance(col, (list, tuple)) and len(col) >= 3:
            r, g, b = col[0], col[1], col[2]
            return r > 0.75 and 0.30 < g < 0.72 and b < 0.45   # DISH orange variants (#EC6A38 / #FB9E00)
    except Exception: pass
    return False

def extract(pdf_path, qid, workflow_title, out_path=None):
    steps = []
    with pdfplumber.open(pdf_path) as pdf:
        pages = pdf.pages
        # the title line is repeated on every page -> use it to cut off the caption
        title = workflow_title.strip().lower()
        n = 0
        for pi, page in enumerate(pages):
            txt = page.extract_text() or ""
            lines = [l.strip() for l in txt.splitlines() if l.strip()]
            cap_lines = []
            for l in lines:
                ll = l.lower().strip()
                if title and ll == title: continue                 # repeated header title
                if re.match(r"^\d+\s+of\s+\d+$", ll): continue   # page number
                if ll in ("d i s h", "dish", "by metro"): continue
                if "scan to go to the interactive player" in ll: continue
                cap_lines.append(l)
            caption = " ".join(cap_lines).strip()
            if not caption or len(caption) < 8:   # QR / empty page
                continue
            # orange-highlighted word(s)
            hl = []
            try:
                words = page.extract_words(extra_attrs=["non_stroking_color"], use_text_flow=True)
                # group orange chars into words via chars
                cur = []
                for ch in page.chars:
                    if _is_orange(ch) and ch.get("text", "").strip():
                        cur.append(ch["text"])
                    elif cur:
                        hl.append("".join(cur).strip()); cur = []
                if cur: hl.append("".join(cur).strip())
            except Exception: pass
            highlight = " ".join([h for h in hl if h]).strip().strip(".,")
            n += 1
            steps.append({"step": n, "action": "info" if not highlight else "click",
                          "caption": caption, "highlight": highlight})
    out = {"id": qid, "title": workflow_title, "workflow_title": workflow_title,
           "source": Path(pdf_path).name, "steps": steps}
    if out_path:
        Path(out_path).write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out

if __name__ == "__main__":
    pdf, qid, wf = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    outp = sys.argv[4] if len(sys.argv) > 4 else "recipes/Q%02d_script.json" % qid
    res = extract(pdf, qid, wf, outp)
    print("extracted %d steps -> %s" % (len(res["steps"]), outp))
    for s in res["steps"]:
        print("  %2d [%s] %s" % (s["step"], s["highlight"], s["caption"][:70]))
