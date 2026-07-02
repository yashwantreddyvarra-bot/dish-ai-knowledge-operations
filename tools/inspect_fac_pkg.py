# Confirms URLs + edit pencils + Add buttons for Facilities, Packaging profiles, Customers.
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
B="https://netherlands.sandbox.myplace.dish.co"
with sync_playwright() as p:
    b=p.chromium.launch(headless=True); pg=b.new_context(viewport={"width":1440,"height":900}).new_page()
    pg.goto(LOGIN_URL,wait_until="domcontentloaded"); pg.wait_for_timeout(1500)
    (first(pg,['input[type=email]','input']) or pg).fill(EMAIL)
    (first(pg,['button:has-text("Continue")','button[type=submit]'])).click(); pg.wait_for_timeout(1500)
    (first(pg,['input[type=password]'])).fill(PASSWORD)
    (first(pg,['button:has-text("Log in")','button[type=submit]'])).click(); pg.wait_for_timeout(4000)
    for u in ["/cm/facilities","/cm/packagingprofiles","/cm/packageprofiles","/cm/customers"]:
        try:
            pg.goto(B+u,wait_until="domcontentloaded"); pg.wait_for_timeout(2200)
            pencils=pg.locator('[data-track-button-id="edit-item"]').count()
            adds=pg.evaluate("""() => [...new Set([...document.querySelectorAll('button,a')].map(e=>(e.innerText||'').trim()).filter(t=>t&&/add|\\+/i.test(t)&&t.length<35))].slice(0,8).join(' | ')""")
            log("URL %s -> %s | pencils=%d | adds: %s"%(u,pg.url,pencils,adds))
        except Exception as e: log("goto %s err %s"%(u,str(e)[:60]))
    Path(ROOT/"output"/"facpkg_inspect.txt").write_text("\n".join(out),encoding="utf-8"); print("DONE"); b.close()
