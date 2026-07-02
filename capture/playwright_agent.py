# capture/playwright_agent.py - Layer 1: full 20-step live capture, aligned to the script.
# Each captured screenshot is tagged with the script step number it belongs to, so the
# PDF/video pages line up 1:1 (no "pending" gaps, no caption/image mismatch).
import sys, json, argparse
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import (LOGIN_URL, PRODUCTS_URL, MENUS_URL, EMAIL, PASSWORD,
                             PRODUCT_NAME, PRODUCT_PRICE, VAT_PREF,
                             PRODUCT_CATEGORY_PREF, MENU_PREF, SS_DIR, BASE_OUT)
from playwright.sync_api import sync_playwright

SS = Path(SS_DIR); SS.mkdir(parents=True, exist_ok=True)
MANIFEST = Path(BASE_OUT) / "manifest.json"
shots = []  # {step, screenshot, url}

def snap(page, step):
    path = SS / ("step_%02d.png" % step)
    try: page.screenshot(path=str(path))
    except Exception as e: print("  snap fail step", step, e)
    shots.append({"step": step, "screenshot": str(path), "url": page.url})
    print("  captured step %02d" % step); sys.stdout.flush()

def save_manifest():
    shots.sort(key=lambda s: s["step"])
    MANIFEST.write_text(json.dumps({"product_name": PRODUCT_NAME, "product_price": PRODUCT_PRICE,
        "workflow_title": "Adding a product and assigning it to a menu",
        "recorded_at": datetime.now(timezone.utc).isoformat(), "screenshots": shots}, indent=2))
    print("manifest ->", MANIFEST, "(%d steps)" % len(shots)); sys.stdout.flush()

def settle(page, ms=2600):
    """Wait for the SPA to finish rendering (no spinner frames)."""
    try: page.wait_for_load_state("load", timeout=8000)
    except Exception: pass
    for sel in ("mat-spinner", ".mat-spinner", ".loading", "[class*=spinner]"):
        try: page.wait_for_selector(sel, state="detached", timeout=2500)
        except Exception: pass
    page.wait_for_timeout(ms)

def click_first(page, sels, t=3000):
    for s in sels:
        try:
            loc = page.locator(s).first; loc.wait_for(state="visible", timeout=t); loc.click(); return True
        except Exception: continue
    return False

def fill_first(page, sels, val, t=3000):
    for s in sels:
        try:
            loc = page.locator(s).first; loc.wait_for(state="visible", timeout=t); loc.fill(val); return True
        except Exception: continue
    return False

def open_dropdown_pick(page, nth, prefs):
    """Open the nth app-dropdown/combobox and click a preferred option in the overlay."""
    triggers = ['app-dropdown', 'app-dropdown-radio-button', 'mat-select', '[role="combobox"]']
    opened = False
    for t in triggers:
        loc = page.locator(t)
        try:
            if loc.count() > nth:
                loc.nth(nth).click(timeout=2500); opened = True; break
        except Exception: continue
    if not opened: return None
    page.wait_for_timeout(700)
    for p in prefs + [None]:
        opts = ([ 'mat-option:has-text("%s")' % p, '[role="option"]:has-text("%s")' % p,
                  '.cdk-overlay-container *:has-text("%s")' % p ] if p
                else ['mat-option', '[role="option"]', '.cdk-overlay-container li'])
        for s in opts:
            try:
                o = page.locator(s).first; o.wait_for(state="visible", timeout=1500); o.click(); return p or "first"
            except Exception: continue
    try: page.keyboard.press("Escape")
    except Exception: pass
    return None

def safe(fn, *a):
    try: return fn(*a)
    except Exception as e: print("  warn:", str(e)[:110]); sys.stdout.flush()

def run(page):
    # ---- product-create half ----
    page.goto(LOGIN_URL, wait_until="domcontentloaded"); settle(page, 1500)
    fill_first(page, ['input[type="email"]', 'input'], EMAIL)
    click_first(page, ['button:has-text("Continue")', 'button[type="submit"]']); page.wait_for_timeout(1500)
    fill_first(page, ['input[type="password"]'], PASSWORD)
    click_first(page, ['button:has-text("Log in")', 'button[type="submit"]'])
    settle(page, 3500)
    snap(page, 1)                                            # 1 welcome/dashboard
    # 2 open Products menu in sidebar
    safe(click_first, page, ['span:has-text("Products")', 'a:has-text("Products")']); page.wait_for_timeout(900); snap(page, 2)
    # 3 products list
    page.goto(PRODUCTS_URL, wait_until="domcontentloaded"); settle(page); snap(page, 3)
    # 4 add product form
    page.goto(PRODUCTS_URL.rstrip("/") + "/(aside_content:createproduct)", wait_until="domcontentloaded"); settle(page); snap(page, 4)
    # 5 name
    fill_first(page, ['input[formcontrolname="name"]'], PRODUCT_NAME); page.wait_for_timeout(500); snap(page, 5)
    # 6 product group (dropdown 0)
    safe(open_dropdown_pick, page, 0, PRODUCT_CATEGORY_PREF); page.wait_for_timeout(500); snap(page, 6)
    # 7 turnover (dropdown 1)
    safe(open_dropdown_pick, page, 1, ["Low VAT", "Food", "Drinks"]); page.wait_for_timeout(500); snap(page, 7)
    # 8 price
    fill_first(page, ['#article_price', 'input[placeholder="0.00"]'], PRODUCT_PRICE); page.wait_for_timeout(500); snap(page, 8)
    # 9 save
    safe(click_first, page, ['button:has-text("Save"):not(:has-text("add new"))', 'button:has-text("Save")']); settle(page, 2500); snap(page, 9)
    # 10 search field
    page.goto(PRODUCTS_URL, wait_until="domcontentloaded"); settle(page)
    fill_first(page, ['input[placeholder*="Search" i]', 'input[type="search"]'], PRODUCT_NAME); page.wait_for_timeout(1500); snap(page, 10)
    # 11 result (same view)
    snap(page, 11)
    # ---- menu-assignment half ----
    page.goto(MENUS_URL, wait_until="domcontentloaded"); settle(page); snap(page, 12)   # 12 Menus page
    # 13 click first menu in left column
    safe(click_first, page, ['text=%s' % MENU_PREF[0], '.menu-list-item', 'mat-tree-node', 'text=Menu']); page.wait_for_timeout(1200); snap(page, 13)
    # 14 expand a submenu chevron
    safe(click_first, page, ['button[aria-label*="expand" i]', 'mat-icon:has-text("expand_more")', 'mat-icon:has-text("chevron_right")', '.toggle-children']); page.wait_for_timeout(1000); snap(page, 14)
    # 15 expand deeper / repeat
    safe(click_first, page, ['mat-icon:has-text("expand_more")', 'mat-icon:has-text("chevron_right")']); page.wait_for_timeout(1000); snap(page, 15)
    # 16 products column (right)
    snap(page, 16)
    # 17 search product in right column
    fill_first(page, ['input[placeholder*="Search" i]'], PRODUCT_NAME, t=2000); page.wait_for_timeout(1200); snap(page, 17)
    # 18 drag product from right column into a middle category (best-effort CDK drag)
    safe(drag_product, page); page.wait_for_timeout(1200); snap(page, 18)
    # 19 product now in menu (same view)
    snap(page, 19)
    # 20 completion - go to General to send changes
    try:
        page.goto(MENUS_URL.replace("/menus", "/dashboard"), wait_until="domcontentloaded"); settle(page, 1500)
    except Exception: pass
    snap(page, 20)

def drag_product(page):
    src = page.locator('text=%s' % PRODUCT_NAME).last
    tgt = page.locator('text=Salads, text=Food, text=Drinks').first
    box_s = src.bounding_box(); box_t = tgt.bounding_box()
    if not box_s or not box_t: return
    page.mouse.move(box_s["x"]+box_s["width"]/2, box_s["y"]+box_s["height"]/2)
    page.mouse.down(); page.wait_for_timeout(200)
    # move in steps so Angular CDK registers the drag
    sx, sy = box_s["x"]+20, box_s["y"]+10; tx, ty = box_t["x"]+40, box_t["y"]+10
    for i in range(1, 11):
        page.mouse.move(sx+(tx-sx)*i/10, sy+(ty-sy)*i/10); page.wait_for_timeout(40)
    page.mouse.up()

def main(headless=False, slowmo=250):
    print("FULL 20-step LIVE capture starting..."); sys.stdout.flush()
    with sync_playwright() as p:
        b = p.chromium.launch(headless=headless, slow_mo=slowmo)
        page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.set_default_timeout(8000)
        try:
            run(page); print("LIVE capture finished (20 steps).")
        except Exception as e:
            print("capture stopped:", str(e)[:160])
        finally:
            save_manifest(); page.wait_for_timeout(500); b.close()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true"); ap.add_argument("--slowmo", type=int, default=250)
    a = ap.parse_args(); main(headless=a.headless, slowmo=a.slowmo)
