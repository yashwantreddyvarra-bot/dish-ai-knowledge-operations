"""
resolver.py - SEE: self-healing element resolution.

Instead of hard-coding selectors per question, the engine asks for a *semantic target*
("edit_pencil", "save_button", "product_group_field"). The resolver returns a RANKED list
of selector strategies to try, ordered by what has worked before on similar pages
(self-healing). When a selector succeeds, the engine calls record_success(); the resolver
remembers it, so reliability climbs over time instead of needing hand-tuning.

If a model is configured (llm.available()), locate_with_vision() can find an element from a
screenshot when every selector fails - the last line of defence against UI changes.
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "output" / "resolver_cache.json"

# Semantic target -> base strategies (most-specific first). These generalise every selector
# list we used across Q1-Q25 into one shared, reusable library.
LIBRARY = {
    "edit_pencil":      ['tbody tr:nth-child(1) [data-track-button-id="edit-item"]',
                         '[data-track-button-id="edit-item"]', 'button.edit-item-button'],
    "duplicate_icon":   ['tbody tr:nth-child(1) [data-track-button-id="duplicate-item"]',
                         '[data-track-button-id="duplicate-item"]', 'tbody tr:nth-child(1) button:nth-of-type(2)'],
    "delete_icon":      ['tbody tr:nth-child(1) [data-track-button-id="delete-item"]',
                         '[data-track-button-id="delete-item"]', 'tbody tr:nth-child(1) button:nth-of-type(3)'],
    "confirm_delete":   ['button:has-text("Delete")', '[data-track-button-id*="confirm" i]'],
    "save_button":      ['app-product-information button:has-text("Save")',
                         'button:has-text("Save"):not(:has-text("add"))', 'button:has-text("Save")'],
    "cancel_button":    ['app-product-information button:has-text("Cancel")', 'button:has-text("Cancel")'],
    "add_product":      ['button:has-text("Add product")', 'a:has-text("Add product")'],
    "filter_button":    ['button:has-text("Filter")'],
    "apply_filters":    ['button:has-text("Apply filters")', 'button:has-text("Apply Filters")'],
    "columns_button":   ['button:has-text("Columns")', 'text=Columns'],
    "search_input":     ['input[placeholder*="earch" i]', '[class*="search"] input'],
    "product_info_tab": ['text=Product information', 'text=Product Information'],
    "product_codes_tab":['text=Product codes'],
    "images_tab":       ['text=Images'],
    "product_desc_tab": ['text=Product description'],
    "name_field":       ['input[formcontrolname*="name" i]', 'input[name*="name" i]'],
    "price_field":      ['input:below(:text-is("Prices"))', 'input:near(:text-is("Price"))'],
    "allergens_section":['app-product-information :text-is("Allergens")', ':nth-match(:text-is("Allergens"), 2)'],
    "additives_section":['app-product-information :text-is("Additives")', ':text-is("Additives")'],
    "general_group":    [':nth-match(button:text-is("General"), 1)', 'button:has-text("General")'],
    "general_sub":      [':nth-match(button:text-is("General"), 2)'],
    "send_button":      ['button:has-text("Send")'],
}

# nav items by visible label -> sidebar button (Products group must be open first for sub-items)
def nav(label):
    return ['button:text-is("%s")' % label, 'span:has-text("%s")' % label, 'text=%s' % label]


def _page_sig(url):
    """A coarse page signature so learning generalises across product ids etc."""
    u = re.sub(r"/\d+", "/:id", url or "")
    u = re.sub(r"\(aside_content:[^/)]+", "(aside", u)
    return u.split("?")[0][-80:]


def _load():
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(d):
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(d, indent=2), encoding="utf-8")
    except Exception:
        pass


def strategies(target, url=""):
    """Ranked selectors to try for a semantic target, learned ones first."""
    base = LIBRARY.get(target, [])
    cache = _load().get(_page_sig(url), {}).get(target, {})
    # sort base strategies by recorded success count (desc), unknown keep original order
    ranked = sorted(base, key=lambda s: -cache.get(s, 0))
    # include any learned selector not already in base
    learned = [s for s in cache if s not in base]
    learned.sort(key=lambda s: -cache[s])
    return learned + ranked


def record_success(target, selector, url=""):
    """Engine calls this when a selector worked, so it floats to the top next time."""
    d = _load()
    sig = _page_sig(url)
    d.setdefault(sig, {}).setdefault(target, {})
    d[sig][target][selector] = d[sig][target].get(selector, 0) + 1
    _save(d)


def pick_element(description, candidates):
    """The accurate path: GPT chooses the BEST matching control from a list of REAL
    on-screen elements (each with its true box). We then use that element's exact box -
    no coordinate guessing. `candidates` = [{text, role, x, y, w, h}, ...].
    Returns the chosen index, or None."""
    from . import llm
    if not llm.available() or not candidates:
        return None
    lines = ["%d: [%s] %s" % (i, c.get("role", ""), (c.get("text", "") or "")[:55])
             for i, c in enumerate(candidates)]
    prompt = ("You are locating one UI control in the DISH POS Backoffice.\n"
              "Instruction for this step: \"%s\".\n\n"
              "On-screen controls (index: [role] label):\n%s\n\n"
              "Reply with ONLY the index number of the control the instruction refers to, "
              "or -1 if none fits." % (description, "\n".join(lines)))
    ans = llm.ask_text(prompt, max_tokens=8)
    try:
        m = re.search(r"-?\d+", ans or "")
        i = int(m.group(0)) if m else -1
        return i if 0 <= i < len(candidates) else None
    except Exception:
        return None


def locate_with_vision(target, screenshot_path):
    """Last-resort: ask a vision model for the element's box when selectors fail.
    Returns [x,y,w,h] in image pixels, or None (no model / not found)."""
    from . import llm
    if not llm.available():
        return None
    ans = llm.ask_vision(
        "Return ONLY a JSON array [x,y,w,h] (pixels) for the bounding box of the "
        "'%s' UI element in this DISH POS screenshot. If absent, return []." % target,
        screenshot_path)
    try:
        m = re.search(r"\[\s*\d[\d,\s.]*\]", ans or "")
        box = json.loads(m.group(0)) if m else []
        return [int(v) for v in box][:4] if len(box) == 4 else None
    except Exception:
        return None


def stats():
    d = _load()
    return {"pages_learned": len(d),
            "targets_learned": sum(len(v) for v in d.values())}
