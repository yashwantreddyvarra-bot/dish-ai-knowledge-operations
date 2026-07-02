"""
autorecipe.py - PLAN: turn an official PDF/HTML into a step script (and a capture plan)
automatically. This codifies what was being done by hand for every question.

  steps_from_pdf(path)   -> [captions]   (iorad export format)
  steps_from_html(path)  -> [captions]   (<li> list or prose)
  build_script(qid, ...) -> writes recipes/QNN_script.json
  build_capture(qid)     -> writes recipes/QNN_capture.json using semantic targets

Caption -> semantic-target mapping is heuristic (keyword based) by default; if a model is
configured it is upgraded to LLM planning that reads each caption and the resolver target
library and picks the best target. The capture plan then uses resolver.strategies() so it
self-heals at run time.
"""
import re, json
from pathlib import Path
from . import resolver

ROOT = Path(__file__).resolve().parent.parent
REC = ROOT / "recipes"

# keyword -> (semantic target, action)  for heuristic planning
KW = [
    (r"\bpencil|edit icon|editing icon\b", "edit_pencil"),
    (r"\bduplicat|copy\b",                 "duplicate_icon"),
    (r"\bdelete icon|deleting icon|bin\b", "delete_icon"),
    (r"\bclick.*delete\b|confirm",         "confirm_delete"),
    (r"\bsave\b",                          "save_button"),
    (r"\badd product\b",                   "add_product"),
    (r"\bfilter\b",                        "filter_button"),
    (r"\bapply filter",                    "apply_filters"),
    (r"\bcolumns\b",                       "columns_button"),
    (r"\bsearch\b",                        "search_input"),
    (r"\bproduct information\b",           "product_info_tab"),
    (r"\bproduct codes\b",                 "product_codes_tab"),
    (r"\bimages\b",                        "images_tab"),
    (r"\bproduct description\b",           "product_desc_tab"),
    (r"\bname of the product|the name\b",  "name_field"),
    (r"\bprice\b",                         "price_field"),
    (r"\ballergen",                        "allergens_section"),
    (r"\badditive",                        "additives_section"),
    (r"\bsend\b",                          "send_button"),
]


def _clean(t):
    return re.sub(r"\s+", " ", t).strip()


def steps_from_pdf(path):
    import pdfplumber
    p = pdfplumber.open(path)
    n = len(p.pages)
    title = _clean((p.pages[0].extract_text() or "").split("\n")[0])
    caps = []
    for i, pg in enumerate(p.pages, 1):
        t = (pg.extract_text() or "").replace("\n", " ")
        t = t.replace(title, "")
        t = re.sub(r"\s*%d of %d\s*$" % (i, n), "", t)
        t = _clean(t)
        if not t:
            continue
        low = t.lower()
        if "scan to go" in low or "interactive player" in low:
            continue
        caps.append(t)
    return caps, title


def steps_from_html(path):
    t = Path(path).read_text(encoding="utf-8", errors="ignore")
    lis = [re.sub(r"<[^>]+>", " ", x) for x in re.findall(r"<li[^>]*>(.*?)</li>", t, flags=re.S)]
    lis = [_clean(x) for x in lis if _clean(x) and len(_clean(x)) > 3]
    if len(lis) >= 3:
        return lis
    # fall back to prose after "Step-by-step"
    vis = _clean(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style).*?</\1>", "", t, flags=re.S)))
    i = vis.lower().find("step-by-step")
    seg = vis[i:i + 1500] if i >= 0 else vis[:1500]
    return [s.strip() for s in re.split(r"(?<=[.])\s+", seg) if len(s.strip()) > 12][:14]


def _target_for(caption):
    low = caption.lower()
    for pat, tgt in KW:
        if re.search(pat, low):
            return tgt
    return None


def _highlight_kw(caption):
    m = re.search(r'"([^"]{2,30})"', caption) or \
        re.search(r"(?:Click on|Click the|Select|Go to|click on)\s+([A-Z][\w +/-]{1,24})", caption)
    return (m.group(1).strip(" .") if m else "")


def build_script(qid, captions, title, source=""):
    steps = []
    for i, c in enumerate(captions, 1):
        info = i == 1 or "that's it" in c.lower() or "you completed" in c.lower()
        steps.append({"step": i, "action": "info" if info else "click",
                      "caption": c, "highlight": _highlight_kw(c)})
    obj = {"id": qid, "title": title, "workflow_title": title,
           "source": source, "steps": steps}
    (REC / ("Q%02d_script.json" % qid)).write_text(json.dumps(obj, indent=2), encoding="utf-8")
    return obj


def build_capture(qid):
    """Generate a capture plan from the script using semantic targets + resolver strategies."""
    script = json.loads((REC / ("Q%02d_script.json" % qid)).read_text(encoding="utf-8"))
    actions = [{"goto": "PRODUCTS", "settle": 2600}]
    for st in script["steps"]:
        tgt = _target_for(st["caption"])
        snap = {"snap": st["step"]}
        if tgt:
            sels = resolver.strategies(tgt)
            snap["highlight"] = sels
            # click targets that change the page
            if tgt in ("edit_pencil", "product_info_tab", "images_tab", "product_desc_tab",
                       "product_codes_tab", "filter_button", "columns_button", "add_product"):
                actions.append({"click": sels, "t": 2800})
                actions.append({"wait": 1200})
        actions.append(snap)
    cj = {"qid": qid, "title": script["title"], "workflow_title": script["title"],
          "vars": {}, "actions": actions, "_note": "auto-generated; refine if a step needs special handling"}
    (REC / ("Q%02d_capture.json" % qid)).write_text(json.dumps(cj, indent=2), encoding="utf-8")
    return cj


def from_pdf(qid, pdf_path, source=None):
    caps, title = steps_from_pdf(pdf_path)
    build_script(qid, caps, title, source or Path(pdf_path).name)
    build_capture(qid)
    return len(caps)


if __name__ == "__main__":
    import sys
    qid, pdf = int(sys.argv[1]), sys.argv[2]
    print("generated %d steps for Q%02d" % (from_pdf(qid, pdf), qid))
