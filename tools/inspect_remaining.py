# Dumps field selectors for the screens behind Q05 (filter), Q12/Q23 (product-group edit),
# Q15 (menu edit -> derived checkbox), Q20 (store price-level section).
import sys, json
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
out={}
B="https://netherlands.sandbox.myplace.dish.co"
DUMP="""() => {
  const n=s=>(s||'').trim().replace(/\\s+/g,' ');
  return JSON.stringify({
    labels:[...new Set([...document.querySelectorAll('label,mat-label,.label,legend,h3,h4,th')].map(e=>n(e.innerText)).filter(t=>t&&t.length<32))],
    ctrls:[...new Set([...document.querySelectorAll('[formcontrolname]')].map(e=>e.tagName.toLowerCase()+'[formcontrolname=\"'+e.getAttribute('formcontrolname')+'\"]'))],
    btns:[...new Set([...document.querySelectorAll('button,a,[role=button]')].map(e=>n(e.innerText)).filter(t=>t&&t.length<26))].slice(0,18)
  });
}"""
with sync_playwright() as p:
    b=p.chromium.launch(headless=True); pg=b.new_context(viewport={"width":1440,"height":900}).new_page()
    pg.goto(LOGIN_URL,wait_until="domcontentloaded"); pg.wait_for_timeout(1500)
    (first(pg,['input[type=email]','input']) or pg).fill(EMAIL)
    (first(pg,['button:has-text("Continue")','button[type=submit]'])).click(); pg.wait_for_timeout(1500)
    (first(pg,['input[type=password]'])).fill(PASSWORD)
    (first(pg,['button:has-text("Log in")','button[type=submit]'])).click(); pg.wait_for_timeout(4000)

    # Q05: products overview -> Filter panel
    pg.goto(PRODUCTS_URL,wait_until="domcontentloaded"); pg.wait_for_timeout(2500)
    fb=first(pg,['button:has-text("Filter")','text=Filter'])
    if fb: fb.click(); pg.wait_for_timeout(1500)
    out["Q05_FILTER"]=pg.evaluate(DUMP)

    # Q12/Q23: product group edit
    pg.goto(B+"/cm/productgroups",wait_until="domcontentloaded"); pg.wait_for_timeout(2500)
    pen=first(pg,['tbody tr:nth-child(1) [data-track-button-id="edit-item"]','[data-track-button-id="edit-item"]'])
    if pen: pen.click(); pg.wait_for_timeout(3000)
    out["Q12_Q23_PRODUCTGROUP_EDIT"]=pg.evaluate(DUMP)

    # Q15: menus -> edit/add -> derived menu checkbox
    pg.goto(B+"/cm/menus",wait_until="domcontentloaded"); pg.wait_for_timeout(2500)
    pen=first(pg,['tbody tr:nth-child(1) [data-track-button-id="edit-item"]','[data-track-button-id="edit-item"]'])
    if pen: pen.click(); pg.wait_for_timeout(3000)
    out["Q15_MENU_EDIT"]=pg.evaluate(DUMP)

    Path(ROOT/"output"/"remaining_forms.txt").write_text(json.dumps(out,indent=1),encoding="utf-8")
    print(json.dumps(out,indent=1)); print("DONE"); b.close()
