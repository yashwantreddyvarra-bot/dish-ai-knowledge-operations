# Logs in (via config) and dumps the products table's first-row action icons,
# so we can find the exact 'edit pencil' selector. Output -> output/row_inspect.txt
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from config.settings import LOGIN_URL, PRODUCTS_URL, EMAIL, PASSWORD
from playwright.sync_api import sync_playwright

def first(page, sels, t=4000):
    for s in sels:
        try:
            l=page.locator(s).first; l.wait_for(state="visible", timeout=t); return l
        except Exception: pass
    return None

with sync_playwright() as p:
    b=p.chromium.launch(headless=True); pg=b.new_context(viewport={"width":1440,"height":900}).new_page()
    pg.goto(LOGIN_URL, wait_until="domcontentloaded"); pg.wait_for_timeout(1500)
    (first(pg,['input[type=email]','input']) or pg).fill(EMAIL)
    (first(pg,['button:has-text("Continue")','button[type=submit]'])).click(); pg.wait_for_timeout(1500)
    (first(pg,['input[type=password]'])).fill(PASSWORD)
    (first(pg,['button:has-text("Log in")','button[type=submit]'])).click(); pg.wait_for_timeout(4000)
    pg.goto(PRODUCTS_URL, wait_until="domcontentloaded"); pg.wait_for_timeout(3000)
    info = pg.evaluate("""() => {
        const row = document.querySelector('tbody tr');
        if(!row) return 'NO ROW';
        const cell = row.querySelector('td');
        const els = [...row.querySelectorAll('a,button,dish-icon,mat-icon,i,svg,[role=button],[data-testid],[title],[class*=edit],[class*=pencil],[class*=delete]')];
        return els.slice(0,12).map(e => e.tagName+' | testid='+(e.getAttribute('data-testid')||'')+' | title='+(e.getAttribute('title')||'')+' | class='+(e.className||'').toString().slice(0,40)+' | href='+(e.getAttribute('href')||'')).join('\\n')
                + '\\n---FIRST CELL HTML---\\n' + (cell? cell.outerHTML.slice(0,800):'');
    }""")
    Path(ROOT/"output"/"row_inspect.txt").write_text(info, encoding="utf-8")
    print("dumped row inspect"); b.close()
