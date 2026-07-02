# Finds how the Products list search actually filters, so Q1 step 10 works.
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from config.settings import LOGIN_URL, PRODUCTS_URL, EMAIL, PASSWORD
from playwright.sync_api import sync_playwright

def first(page, sels, t=4000):
    for s in sels:
        try:
            l=page.locator(s).first; l.wait_for(state="visible",timeout=t); return l
        except Exception: pass
    return None
out=[]
def log(*a): out.append(" ".join(str(x) for x in a)); print(*a)

with sync_playwright() as p:
    b=p.chromium.launch(headless=True); pg=b.new_context(viewport={"width":1440,"height":900}).new_page()
    pg.goto(LOGIN_URL,wait_until="domcontentloaded"); pg.wait_for_timeout(1500)
    (first(pg,['input[type=email]','input']) or pg).fill(EMAIL)
    (first(pg,['button:has-text("Continue")','button[type=submit]'])).click(); pg.wait_for_timeout(1500)
    (first(pg,['input[type=password]'])).fill(PASSWORD)
    (first(pg,['button:has-text("Log in")','button[type=submit]'])).click(); pg.wait_for_timeout(4000)
    pg.goto(PRODUCTS_URL,wait_until="domcontentloaded"); pg.wait_for_timeout(2800)

    def rows(): return pg.locator("tbody tr").count()
    # list every input on the page so we know the real search selector
    inputs = pg.evaluate("""() => [...document.querySelectorAll('input')].map(e=>({type:e.type,ph:e.placeholder,fc:e.getAttribute('formcontrolname'),cls:(e.className||'').slice(0,40)}))""")
    log("INPUTS on products page:"); [log("  ", str(i)) for i in inputs]
    log("rows before:", rows())

    se = first(pg, ['input[type="search"]','input[placeholder*="Search" i]','input[placeholder*="search" i]'])
    if not se:
        log("NO search input found");
    else:
        # method 1: fill + wait
        se.fill("Apple"); pg.wait_for_timeout(2000); log("after fill('Apple'):", rows())
        # method 2: + Enter
        se.press("Enter"); pg.wait_for_timeout(2000); log("after Enter:", rows())
        # method 3: clear + type char-by-char
        se.fill(""); pg.wait_for_timeout(800)
        se.type("Apple", delay=120); pg.wait_for_timeout(2200); log("after type() char-by-char:", rows())
    Path(ROOT/"output"/"search_inspect.txt").write_text("\n".join(out),encoding="utf-8")
    print("DONE"); b.close()
