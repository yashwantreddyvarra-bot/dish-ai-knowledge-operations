# Logs in and, for French menus / Periods / Promotions, navigates there and dumps the URL
# and the "Add ..." button(s) so we can fix Q16/17/18. Output -> output/sections_inspect.txt
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

out=[]
def log(*a): out.append(" ".join(str(x) for x in a)); print(*a)

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width":1440,"height":900}).new_page()
    pg.goto(LOGIN_URL, wait_until="domcontentloaded"); pg.wait_for_timeout(1500)
    (first(pg,['input[type=email]','input']) or pg).fill(EMAIL)
    (first(pg,['button:has-text("Continue")','button[type=submit]'])).click(); pg.wait_for_timeout(1500)
    (first(pg,['input[type=password]'])).fill(PASSWORD)
    (first(pg,['button:has-text("Log in")','button[type=submit]'])).click(); pg.wait_for_timeout(4000)

    for label in ["French menus", "Periods", "Promotions"]:
        pg.goto(PRODUCTS_URL, wait_until="domcontentloaded"); pg.wait_for_timeout(2500)
        nav = first(pg, ['button:text-is("%s")' % label, 'span:has-text("%s")' % label, 'text=%s' % label])
        if nav:
            nav.click(); pg.wait_for_timeout(2500)
        log("\n=== %s ===  URL=%s" % (label, pg.url))
        # dump all Add-ish buttons/links
        adds = pg.evaluate("""() => {
            const out=[];
            for (const e of document.querySelectorAll('button, a, [role=button]')) {
                const t=(e.innerText||'').trim().replace(/\\s+/g,' ');
                if (t && /add|\\+/i.test(t) && t.length<40) out.push(e.tagName+' | "'+t+'"');
            }
            return [...new Set(out)].slice(0,12).join('\\n');
        }""")
        log(adds or "  (no Add buttons found)")
        # also the page heading
        head = pg.evaluate("""() => { const h=document.querySelector('h1,h2,[class*=title]'); return h?(h.innerText||'').trim().slice(0,40):''; }""")
        log("  heading:", head)

    Path(ROOT/"output"/"sections_inspect.txt").write_text("\n".join(out), encoding="utf-8")
    print("\nDONE"); b.close()
