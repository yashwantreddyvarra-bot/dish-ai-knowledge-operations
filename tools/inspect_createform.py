# Logs in, opens the Add product (create) form, and dumps the header dropdowns
# (Product group / Turnover) + Price field selectors. Output -> stdout + file.
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
    pg.goto(PRODUCTS_URL.rstrip("/") + "/(aside_content:createproduct)", wait_until="domcontentloaded")
    pg.wait_for_timeout(3500)
    log("URL:", pg.url)
    # dump all selects/dropdowns inside the form with their nearby label / formcontrolname
    info = pg.evaluate("""() => {
        const rows=[];
        const els=[...document.querySelectorAll('mat-select, [role="combobox"], select, app-dropdown')];
        els.forEach((e,i)=>{
            const fc=e.getAttribute('formcontrolname')||e.getAttribute('name')||'';
            // find nearest label text
            let lab='';
            let n=e.closest('*');
            // look back for a label sibling
            const cont=e.closest('div,mat-form-field,app-form-field')||e.parentElement;
            if(cont){ const t=(cont.innerText||'').trim().split('\\n')[0]; lab=t.slice(0,25); }
            rows.push(i+': tag='+e.tagName+' fc="'+fc+'" label="'+lab+'" vis='+(e.offsetParent!==null));
        });
        return rows.join('\\n');
    }""")
    log("=== form dropdowns ===\n"+info)
    # price + name fields
    for lbl,sel in [("name",'input[formcontrolname*="name" i]'),
                    ("price",'input[formcontrolname*="price" i]'),
                    ("any input[formcontrolname]",'input[formcontrolname]')]:
        try: log(lbl, "count=", pg.locator(sel).count(), "first fc=", pg.locator(sel).first.get_attribute("formcontrolname"))
        except Exception as e: log(lbl, "err", str(e)[:60])
    Path(ROOT/"output"/"createform_inspect.txt").write_text("\n".join(out), encoding="utf-8")
    print("DONE"); b.close()
