# Dumps the product-EDIT form fields (for fixing Q07 highlight selectors).
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
B="https://netherlands.sandbox.myplace.dish.co"
with sync_playwright() as p:
    b=p.chromium.launch(headless=True); pg=b.new_context(viewport={"width":1440,"height":900}).new_page()
    pg.goto(LOGIN_URL,wait_until="domcontentloaded"); pg.wait_for_timeout(1500)
    (first(pg,['input[type=email]','input']) or pg).fill(EMAIL)
    (first(pg,['button:has-text("Continue")','button[type=submit]'])).click(); pg.wait_for_timeout(1500)
    (first(pg,['input[type=password]'])).fill(PASSWORD)
    (first(pg,['button:has-text("Log in")','button[type=submit]'])).click(); pg.wait_for_timeout(4000)
    pg.goto(PRODUCTS_URL,wait_until="domcontentloaded"); pg.wait_for_timeout(2500)
    pen=first(pg,['tbody tr:nth-child(1) [data-track-button-id="edit-item"]','[data-track-button-id="edit-item"]'])
    if pen: pen.click(); pg.wait_for_timeout(3500)
    dump=pg.evaluate("""() => {
      const norm=s=>(s||'').trim().replace(/\\s+/g,' ');
      const ctrls=[...document.querySelectorAll('[formcontrolname]')].map(e=>e.tagName.toLowerCase()+'[formcontrolname="'+e.getAttribute('formcontrolname')+'"]');
      const labels=[...document.querySelectorAll('label,mat-label,.label,legend,h3,h4')].map(e=>norm(e.innerText)).filter(t=>t&&t.length<32);
      return JSON.stringify({labels:[...new Set(labels)],ctrls:[...new Set(ctrls)]},null,1);
    }""")
    Path(ROOT/"output"/"product_form.txt").write_text(dump,encoding="utf-8"); print(dump); print("DONE"); b.close()
