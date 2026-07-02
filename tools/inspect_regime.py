# Logs in and tries to reach the General settings / Stores / establishment page and the
# 'Regime Forfettario' checkbox. Dumps findings to stdout + output/regime_inspect.txt
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
    pg.goto(PRODUCTS_URL, wait_until="domcontentloaded"); pg.wait_for_timeout(2500)

    # click the General GROUP button and dump what appears
    g = first(pg, ['button:text-is("General")','button:has-text("General")'])
    if g: g.click(); pg.wait_for_timeout(1500)
    log("URL after General group click:", pg.url)
    # list nav buttons that look like General children
    items = pg.evaluate("""() => [...document.querySelectorAll('button,a')].map(e=>(e.innerText||'').trim()).filter(t=>t&&t.length<26)""")
    # show items around General
    log("nav items sample:", " | ".join(items[:60]))

    # try direct URLs for stores/settings
    for u in ["/cm/stores","/cm/store","/cm/general","/cm/settings","/cm/establishments","/cm/establishment","/cm/company"]:
        try:
            pg.goto("https://netherlands.sandbox.myplace.dish.co"+u, wait_until="domcontentloaded"); pg.wait_for_timeout(1800)
            has_pencil = pg.locator('[data-track-button-id="edit-item"]').count()
            has_regime = pg.locator('text=Regime').count() + pg.locator('text=Forfettario').count()
            log("URL %s -> %s | edit-pencils=%d | regime-matches=%d" % (u, pg.url, has_pencil, has_regime))
            if pg.url.rstrip("/").endswith(u) and has_pencil:
                # open first row editor and look for Regime Forfettario
                try:
                    pg.locator('[data-track-button-id="edit-item"]').first.click(); pg.wait_for_timeout(2500)
                    rf = pg.locator('text=Regime').count()+pg.locator('text=Forfettario').count()
                    snd = pg.locator('button:has-text("Send")').count()
                    log("   opened editor: regime-matches=%d send-buttons=%d url=%s"%(rf,snd,pg.url))
                    # dump any checkbox labels containing Regime/Forfettario
                    labels = pg.evaluate("""() => [...document.querySelectorAll('*')].map(e=>(e.innerText||'').trim()).filter(t=>/forfettario|regime/i.test(t)).slice(0,5)""")
                    log("   regime labels:", labels)
                except Exception as e:
                    log("   editor open err:", str(e)[:80])
        except Exception as e:
            log("goto %s err: %s"%(u,str(e)[:80]))

    Path(ROOT/"output"/"regime_inspect.txt").write_text("\n".join(out), encoding="utf-8")
    print("\nDONE"); b.close()
