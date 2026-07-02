# Dumps real field selectors for the Store-edit (Q20) and Facility Menu-tab (Q22) forms.
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from config.settings import LOGIN_URL, EMAIL, PASSWORD
from playwright.sync_api import sync_playwright

def first(page, sels, t=4000):
    for s in sels:
        try:
            l=page.locator(s).first; l.wait_for(state="visible",timeout=t); return l
        except Exception: pass
    return None
out=[]
def log(*a): out.append(" ".join(str(x) for x in a)); print(*a)
B="https://netherlands.sandbox.myplace.dish.co"
DUMP="""() => {
  const norm=s=>(s||'').trim().replace(/\\s+/g,' ');
  const heads=[...document.querySelectorAll('h1,h2,h3,h4,legend,strong,.title')].map(e=>norm(e.innerText)).filter(t=>t&&t.length<40);
  const labels=[...document.querySelectorAll('label,.label,mat-label')].map(e=>norm(e.innerText)).filter(t=>t&&t.length<40);
  const ctrls=[...document.querySelectorAll('[formcontrolname]')].map(e=>e.tagName.toLowerCase()+'[formcontrolname="'+e.getAttribute('formcontrolname')+'"]');
  const btns=[...document.querySelectorAll('button,a,[role=button]')].map(e=>norm(e.innerText)).filter(t=>t&&t.length<28);
  return JSON.stringify({heads:[...new Set(heads)],labels:[...new Set(labels)],ctrls:[...new Set(ctrls)],btns:[...new Set(btns)].slice(0,25)},null,1);
}"""
with sync_playwright() as p:
    b=p.chromium.launch(headless=True); pg=b.new_context(viewport={"width":1440,"height":900}).new_page()
    pg.goto(LOGIN_URL,wait_until="domcontentloaded"); pg.wait_for_timeout(1500)
    (first(pg,['input[type=email]','input']) or pg).fill(EMAIL)
    (first(pg,['button:has-text("Continue")','button[type=submit]'])).click(); pg.wait_for_timeout(1500)
    (first(pg,['input[type=password]'])).fill(PASSWORD)
    (first(pg,['button:has-text("Log in")','button[type=submit]'])).click(); pg.wait_for_timeout(4000)

    # Q20: store edit form
    pg.goto(B+"/cm/stores",wait_until="domcontentloaded"); pg.wait_for_timeout(2500)
    pen=first(pg,['tbody tr:nth-child(1) [data-track-button-id="edit-item"]','[data-track-button-id="edit-item"]'])
    if pen: pen.click(); pg.wait_for_timeout(3000)
    log("===== Q20 STORE EDIT =====\n"+pg.evaluate(DUMP))

    # Q22: facility -> Menu tab
    pg.goto(B+"/cm/salespoints",wait_until="domcontentloaded"); pg.wait_for_timeout(2500)
    pen=first(pg,['tbody tr:nth-child(1) [data-track-button-id="edit-item"]','[data-track-button-id="edit-item"]'])
    if pen: pen.click(); pg.wait_for_timeout(3000)
    mt=first(pg,['app-aside :text-is("Menu")',':text-is("Menu")'])
    if mt: mt.click(); pg.wait_for_timeout(2500)
    log("\n===== Q22 FACILITY MENU TAB =====\n"+pg.evaluate(DUMP))
    Path(ROOT/"output"/"q20_q22_forms.txt").write_text("\n".join(out),encoding="utf-8"); print("DONE"); b.close()
