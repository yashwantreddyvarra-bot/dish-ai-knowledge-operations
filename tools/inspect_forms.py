# Opens the create-forms for French menu / period / promotion / packaging profile and dumps
# real section headings + field labels + form-control selectors so we can fix highlights.
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
  const radios=[...document.querySelectorAll('mat-radio-button,[type=radio],mat-checkbox,[type=checkbox]')].map(e=>norm(e.innerText)||norm(e.closest('label')?.innerText)).filter(Boolean);
  return JSON.stringify({heads:[...new Set(heads)],labels:[...new Set(labels)],ctrls:[...new Set(ctrls)],radios:[...new Set(radios)]},null,1);
}"""
def opn(pg, url, add):
    pg.goto(url,wait_until="domcontentloaded"); pg.wait_for_timeout(2800)
    a=first(pg, add, t=4000)
    if a: a.click(); pg.wait_for_timeout(2800)
    return pg.evaluate(DUMP)
with sync_playwright() as p:
    b=p.chromium.launch(headless=True); pg=b.new_context(viewport={"width":1440,"height":900}).new_page()
    pg.goto(LOGIN_URL,wait_until="domcontentloaded"); pg.wait_for_timeout(1500)
    (first(pg,['input[type=email]','input']) or pg).fill(EMAIL)
    (first(pg,['button:has-text("Continue")','button[type=submit]'])).click(); pg.wait_for_timeout(1500)
    (first(pg,['input[type=password]'])).fill(PASSWORD)
    (first(pg,['button:has-text("Log in")','button[type=submit]'])).click(); pg.wait_for_timeout(4000)
    for name,url,add in [
        ("FRENCH MENU", B+"/cm/frenchmenus", ['button:has-text("Add French menu")']),
        ("PERIOD",      B+"/cm/timeperiods", ['button:has-text("Add period")']),
        ("PROMOTION",   B+"/cm/promotions",  ['button:has-text("Add promotion")']),
        ("PACKAGING",   B+"/cm/recyclingDeposits", ['button:has-text("Add profile")']),
    ]:
        try: log("\n===== %s =====\n%s"%(name, opn(pg,url,add)))
        except Exception as e: log("\n===== %s ERR %s"%(name,str(e)[:80]))
    Path(ROOT/"output"/"forms_inspect.txt").write_text("\n".join(out),encoding="utf-8"); print("DONE"); b.close()
