# Logs in (via config) and dumps selectors needed for Q4 (composites) and Q5 (search/filter).
# Output -> output/q45_inspect.txt  (printed to stdout too).
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from config.settings import LOGIN_URL, PRODUCTS_URL, EMAIL, PASSWORD
from playwright.sync_api import sync_playwright

def first(page, sels, t=4000):
    for s in sels:
        try:
            l = page.locator(s).first; l.wait_for(state="visible", timeout=t); return l
        except Exception: pass
    return None

out = []
def dump(label, sels):
    found = []
    for s in sels:
        try:
            loc = page.locator(s)
            n = loc.count()
            if n:
                txt = (loc.first.inner_text() or "").strip().replace("\n", " ")[:30]
                found.append("  OK  %-55s count=%d text=%r" % (s, n, txt))
        except Exception as e:
            pass
    out.append("[%s]\n%s" % (label, "\n".join(found) if found else "  (none matched)"))

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_context(viewport={"width":1440,"height":900}).new_page()
    page.goto(LOGIN_URL, wait_until="domcontentloaded"); page.wait_for_timeout(1500)
    (first(page,['input[type=email]','input']) or page).fill(EMAIL)
    (first(page,['button:has-text("Continue")','button[type=submit]'])).click(); page.wait_for_timeout(1500)
    (first(page,['input[type=password]'])).fill(PASSWORD)
    (first(page,['button:has-text("Log in")','button[type=submit]'])).click(); page.wait_for_timeout(4000)
    page.goto(PRODUCTS_URL, wait_until="domcontentloaded"); page.wait_for_timeout(3000)

    out.append("URL: " + page.url)
    dump("search input", ['input[placeholder*="earch" i]', 'input[type="search"]', '[class*="search"] input'])
    dump("Add product button", ['button:has-text("Add product")', 'a:has-text("Add product")', 'button:has-text("Add Product")'])
    dump("Filter button", ['button:has-text("Filter")', '[class*="filter"] button'])
    dump("Columns button", ['button:has-text("Columns")'])
    dump("product group dropdown", ['mat-select', '[role="combobox"]', 'app-dropdown', 'select', 'button:has-text("All")'])

    # open Filter panel and inspect Apply / Delete
    f = first(page, ['button:has-text("Filter")'])
    if f:
        f.click(); page.wait_for_timeout(1500)
        out.append("\n-- after clicking Filter --  URL=" + page.url)
        dump("Apply button", ['button:has-text("Apply")', 'button:has-text("Apply Filters")', 'button:has-text("Apply filters")'])
        dump("Delete all filters", ['button:has-text("Delete all filters")', 'text=Delete all filters', 'button:has-text("Delete")'])
        dump("filter fields", ['input', 'mat-select', '[role="combobox"]'])
        try: page.keyboard.press("Escape")
        except Exception: pass
        page.wait_for_timeout(800)

    # Add product form -> Composites / Add item / Save / Prepare separately
    page.goto(PRODUCTS_URL.rstrip("/") + "/(aside_content:createproduct)", wait_until="domcontentloaded")
    page.wait_for_timeout(3500)
    out.append("\n-- Add product form --  URL=" + page.url)
    dump("Composites section", ['text=Composites', ':text("Composites")', 'h2:has-text("Composites")'])
    dump("Add item", ['text=Add item', 'button:has-text("Add item")', 'a:has-text("Add item")', ':text("Add item")'])
    dump("Prepare separately checkbox", ['text=Prepare composite', 'mat-checkbox:has-text("Prepare")', 'label:has-text("Prepare")'])
    dump("Hide on receipt", ['text=Hide on receipt', 'mat-checkbox:has-text("Hide")'])
    dump("Save button", ['button:has-text("Save")'])
    dump("Name field", ['input[formcontrolname*="name" i]', 'input[name*="name" i]'])
    dump("left menu items", ['app-product :text-is("Composites")', 'a:has-text("Product Information")'])

    Path(ROOT/"output"/"q45_inspect.txt").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
    print("\ndumped ->", ROOT/"output"/"q45_inspect.txt"); b.close()
