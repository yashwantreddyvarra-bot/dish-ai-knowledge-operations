# capture/engine.py - generic, question-driven live capture.
# Reads recipes/Q{NN}_capture.json (an ordered action plan), logs into DISH POS,
# executes the actions, and writes output/manifest_q{NN}.json with screenshots
# tagged to their script step number. One engine for all 25 questions.
import sys, json, argparse, re, os, time
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config.settings import LOGIN_URL, PRODUCTS_URL, MENUS_URL, EMAIL, PASSWORD
from playwright.sync_api import sync_playwright

URLS = {"LOGIN": LOGIN_URL, "PRODUCTS": PRODUCTS_URL, "MENUS": MENUS_URL,
        "CREATE": PRODUCTS_URL.rstrip("/") + "/(aside_content:createproduct)",
        "DASHBOARD": LOGIN_URL.replace("/login", "/dashboard")}


def cloud_headless(default=False):
    """True on Render / Streamlit / Linux servers without a display."""
    flag = os.environ.get("CAPTURE_HEADLESS", "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return True
    if flag in ("0", "false", "no", "off"):
        return False
    if os.environ.get("RENDER") or os.environ.get("RENDER_SERVICE_ID"):
        return True
    if os.environ.get("STREAMLIT_SERVER_PORT"):
        return True
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        return True
    return default


def launch_chromium(playwright, headless=False, slow_mo=250):
    """Launch Chromium; cloud/Docker needs headless + no-sandbox."""
    if headless is None:
        headless = cloud_headless(default=False)
    args = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
            "--disable-blink-features=AutomationControlled"] if headless else []
    if headless:
        slow_mo = min(slow_mo, 50)
    print("ENGINE: chromium headless=%s" % headless, flush=True)
    return playwright.chromium.launch(headless=headless, slow_mo=slow_mo, args=args)


def new_browser_page(browser, viewport=None):
    """New page with consent pre-accepted so the login form is not blocked."""
    ctx = browser.new_context(
        viewport=viewport or {"width": 1440, "height": 900},
        user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    )
    ctx.add_init_script(
        "try{localStorage.setItem('uxp',JSON.stringify({lasthit:Date.now(),event:'consent_status'}));}catch(e){}"
    )
    page = ctx.new_page()
    page.set_default_timeout(8000)
    return page


def _vhint(sels):
    """Turn a selector list into a human description for the model,
    e.g. text=Product group / :text-is("Allergens") / button:has-text("Save") -> the label."""
    for s in (sels if isinstance(sels, list) else [sels]):
        m = re.search(r'text=["\']?([^"\'\]]{2,40})', s) or \
            re.search(r'(?:text-is|has-text)\(["\']([^"\']{2,40})', s)
        if m:
            return "the '%s' control" % m.group(1).strip()
    return None


# Lists the real, visible, interactive controls on the page with their TRUE boxes, so the
# model can pick the right one and we use exact geometry (no coordinate guessing).
_CANDS_JS = """() => {
  const out=[], seen=new Set();
  const els=[...document.querySelectorAll('input,textarea,select,button,a,mat-select,[role="combobox"],[role="button"],[role="checkbox"],[role="tab"]')];
  for(const e of els){
    const r=e.getBoundingClientRect();
    if(r.width<6||r.height<6) continue;
    if(r.bottom<0||r.right<0||r.top>900||r.left>1440) continue;
    let t=(e.innerText||e.value||e.getAttribute('placeholder')||e.getAttribute('aria-label')||'').trim();
    if(!t){ const f=e.closest('div,mat-form-field,app-form-field'); if(f){ t=(f.innerText||'').trim().split('\\n')[0]; } }
    t=t.replace(/\\s+/g,' ').slice(0,55);
    if(!t) continue;
    const key=t+'|'+Math.round(r.x)+'|'+Math.round(r.y);
    if(seen.has(key)) continue; seen.add(key);
    out.push({text:t, role:(e.getAttribute('role')||e.tagName.toLowerCase()),
              x:r.x, y:r.y, w:r.width, h:r.height});
  }
  return out.slice(0,60);
}"""

def ss_dir(qid): d = ROOT / "output" / "screenshots" / ("q%02d" % qid); d.mkdir(parents=True, exist_ok=True); return d
def manifest_path(qid): return ROOT / "output" / ("manifest_q%02d.json" % qid)

# Set by a run when a product the user named isn't in the catalogue (so the build can
# reply "not found" instead of producing a guide for the wrong product).
_NOT_FOUND = {}

def _vars(s, V):
    for k, v in V.items(): s = s.replace("{%s}" % k, str(v))
    return s

def settle(page, ms=2400):
    try: page.wait_for_load_state("load", timeout=8000)
    except Exception: pass
    for sel in ("mat-spinner", ".mat-spinner", "[class*=spinner]"):
        try: page.wait_for_selector(sel, state="detached", timeout=2200)
        except Exception: pass
    page.wait_for_timeout(ms)

def try_each(page, op, sels, t=3000, **kw):
    for s in sels:
        try:
            loc = page.locator(s).first; loc.wait_for(state="visible", timeout=t)
            getattr(loc, op)(**kw); return True
        except Exception: continue
    return False

def _first_loc(page, sels, t=3000):
    """Return (locator, selector) for the first visible match, else (None, None)."""
    for s in (sels if isinstance(sels, list) else [sels]):
        try:
            loc = page.locator(s).first
            loc.wait_for(state="visible", timeout=t)
            return loc, s
        except Exception:
            continue
    return None, None

def drag_drop(page, src_sels, dst_sels, t=3000):
    """Real drag-and-drop using a stepped mouse motion (Angular CDK / HTML5 dnd both need
    genuine mousemove events between down and up, which Locator.drag_to often skips). Drags
    the first visible source element onto the first visible target element. Returns True on
    success so the step's screenshot shows the product actually placed in the menu."""
    src, ssel = _first_loc(page, src_sels, t)
    dst, dsel = _first_loc(page, dst_sels, t)
    if not src or not dst:
        print("  drag: source(%s) or target(%s) not found" % (bool(src), bool(dst))); return False
    try: src.scroll_into_view_if_needed(timeout=1500)
    except Exception: pass
    sb = src.bounding_box(); db = dst.bounding_box()
    if not sb or not db:
        print("  drag: missing geometry"); return False
    sx, sy = sb["x"] + sb["width"]/2, sb["y"] + sb["height"]/2
    dx, dy = db["x"] + db["width"]/2, db["y"] + db["height"]/2
    # 1) Playwright's drag_to dispatches real HTML5 dragstart/dragover/drop events — required
    #    for draggable="true" rows (this app is NOT Angular CDK). Try it first.
    try:
        src.drag_to(dst, timeout=4000); page.wait_for_timeout(900)
        print("  drag (drag_to): %s -> %s" % (ssel, dsel)); return True
    except Exception as e:
        print("  drag_to fallback (%s)" % str(e)[:60])
    # 2) Manual stepped mouse motion as a fallback for custom mouse-event drags.
    try:
        page.mouse.move(sx, sy); page.wait_for_timeout(150)
        page.mouse.down(); page.wait_for_timeout(200)
        steps = 22
        for i in range(1, steps + 1):
            page.mouse.move(sx + (dx-sx)*i/steps, sy + (dy-sy)*i/steps); page.wait_for_timeout(28)
        page.wait_for_timeout(250)            # let the drop target light up before releasing
        page.mouse.up(); page.wait_for_timeout(900)
        print("  drag (mouse): %s -> %s" % (ssel, dsel)); return True
    except Exception as e:
        print("  drag warn:", str(e)[:90])
        try: page.mouse.up()
        except Exception: pass
        return False

def dump_dom(page, tag):
    """Write the page's interactive-element candidates + trimmed HTML so selectors can be
    crafted against the REAL live DOM. Diagnostic only; safe to leave in a recipe."""
    try:
        cands = page.evaluate(_CANDS_JS)
        (ROOT / "output" / ("dom_%s.json" % tag)).write_text(json.dumps(cands, indent=2), encoding="utf-8")
        try:
            (ROOT / "output" / ("dom_%s.html" % tag)).write_text(page.content()[:300000], encoding="utf-8")
        except Exception: pass
        print("  dumped DOM -> output/dom_%s.json (%d candidates)" % (tag, len(cands)))
    except Exception as e:
        print("  dump warn:", str(e)[:90])

def dropdown_pick(page, nth, prefs):
    for trig in ('app-dropdown', 'mat-select', '[role="combobox"]', 'select'):
        loc = page.locator(trig)
        try:
            if loc.count() > nth: loc.nth(nth).click(timeout=2500); break
        except Exception: continue
    else: return None
    page.wait_for_timeout(600)
    for p in (prefs + [None]):
        opts = ([ 'mat-option:has-text("%s")' % p, '[role="option"]:has-text("%s")' % p ] if p
                else ['mat-option', '[role="option"]'])
        for s in opts:
            try:
                o = page.locator(s).first; o.wait_for(state="visible", timeout=1500); o.click(); return p or "first"
            except Exception: continue
    try: page.keyboard.press("Escape")
    except Exception: pass
    return None

def select_field(page, trigger, prefs):
    """Open a specific field (PrimeNG p-select, custom tree input, mat-select, native select)
    by selector and pick the first matching option / tree node. Handles the modern DISH
    components the old dropdown_pick missed (so product group / turnover actually get set)."""
    try:
        page.locator(trigger).first.click(timeout=3500)
    except Exception:
        return None
    page.wait_for_timeout(700)
    for p in (list(prefs) + [None]):
        if p:
            cands = ['[role="option"]:has-text("%s")' % p, '[role="treeitem"]:has-text("%s")' % p,
                     '.p-select-option:has-text("%s")' % p, '.p-tree-node-label:has-text("%s")' % p,
                     'mat-option:has-text("%s")' % p, 'li:has-text("%s")' % p,
                     'span:has-text("%s")' % p]
        else:
            cands = ['[role="option"]', '[role="treeitem"]', '.p-select-option', 'mat-option']
        for s in cands:
            try:
                o = page.locator(s).first
                o.wait_for(state="visible", timeout=1500)
                o.click(); page.wait_for_timeout(400)
                return p or "first"
            except Exception:
                continue
    try: page.keyboard.press("Escape")
    except Exception: pass
    return None

def _login_creds():
    """Read credentials at call time (Render env vars may load after import)."""
    email = (os.getenv("DISH_EMAIL") or EMAIL or "").strip().strip('"').strip("'")
    password = (os.getenv("DISH_PASSWORD") or PASSWORD or "").strip().strip('"').strip("'")
    return email, password


def _angular_fill(page, selectors, value, label="field"):
    """Fill Angular reactive form fields (plain fill() often does not bind)."""
    if not value:
        print("  login: missing %s (set DISH_EMAIL / DISH_PASSWORD)" % label)
        return False
    for s in selectors:
        try:
            loc = page.locator(s).first
            loc.wait_for(state="visible", timeout=10000)
            loc.click(timeout=2000)
            loc.fill("")
            loc.press_sequentially(value, delay=35)
            loc.evaluate("""(el, val) => {
                el.value = val;
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
                el.dispatchEvent(new Event('blur', {bubbles: true}));
            }""", value)
            got = ""
            try:
                got = (loc.input_value(timeout=2000) or "").strip()
            except Exception:
                got = value if label == "password" else ""
            ok = (label == "password" and len(got) == len(value)) or got == value
            if ok or (label == "email" and "@" in got):
                print("  login: filled %s" % label)
                return True
        except Exception:
            continue
    ph = "Your email address" if label == "email" else "Your password"
    try:
        loc = page.get_by_placeholder(ph).first
        loc.wait_for(state="visible", timeout=5000)
        loc.click()
        loc.press_sequentially(value, delay=35)
        print("  login: filled %s via placeholder" % label)
        return True
    except Exception:
        pass
    print("  login: FAILED to fill %s" % label)
    return False


def _click_continue(page):
    """DISH login uses one Continue button for email AND password steps."""
    for sel in ('[data-testid="continueButton"]', 'button.add-item-button[type="submit"]',
                'button:has-text("Continue")', 'button[type="submit"]'):
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=5000)
            loc.click(timeout=5000)
            print("  login: clicked Continue")
            return True
        except Exception:
            continue
    return False


def _wait_password_visible(page, timeout_ms=15000):
    page.wait_for_function("""() => {
        const el = document.querySelector('#password');
        if (!el) return false;
        const st = window.getComputedStyle(el);
        const r = el.getBoundingClientRect();
        return st.display !== 'none' && st.visibility !== 'hidden'
               && r.width > 8 && r.height > 8;
    }""", timeout=timeout_ms)


def _login_error_text(page):
    for sel in ('.login-error', '.form-group-password .login-error',
                '[data-testid="passwordAlertIcon"]'):
        try:
            t = page.locator(sel).first.inner_text(timeout=800).strip()
            if t:
                return t
        except Exception:
            pass
    return ""


def _wait_logged_in(page, timeout_ms=35000):
    """Wait until we leave the login screen (URL or nav chrome)."""
    deadline = time.time() + timeout_ms / 1000.0
    dash = re.compile(r".*/(dashboard|products|menus)(/|$|\?)", re.I)
    while time.time() < deadline:
        url = page.url or ""
        if dash.search(url):
            settle(page, 1500)
            print("  login: reached %s" % url[:80])
            return True
        if "/login" not in url.lower() and "myplace.dish.co" in url:
            settle(page, 1500)
            print("  login: left login page -> %s" % url[:80])
            return True
        for sel in ('app-nav-link', 'app-left-menu', 'span:has-text("Products")',
                    'text=Products', '[class*="left-menu"]'):
            try:
                if page.locator(sel).first.is_visible(timeout=600):
                    print("  login: dashboard nav visible")
                    return True
            except Exception:
                pass
        page.wait_for_timeout(500)
    return False


def _login_debug_shot(page, tag="fail"):
    try:
        d = ROOT / "output" / "screenshots"
        d.mkdir(parents=True, exist_ok=True)
        path = d / ("login_%s.png" % tag)
        page.screenshot(path=str(path), full_page=True)
        print("  login: debug screenshot -> %s" % path)
    except Exception:
        pass


def _dismiss_consent(page):
    """Dismiss Usercentrics cookie banner — it blocks the login form."""
    try:
        page.evaluate("""() => {
            if (window.UC_UI && UC_UI.acceptAllConsents) {
                UC_UI.acceptAllConsents();
                return true;
            }
            return false;
        }""")
        page.wait_for_timeout(500)
        print("  login: dismissed consent via UC_UI")
        return True
    except Exception:
        pass
    for sel in ('button:has-text("Deny")', 'button:has-text("Decline")',
                'button:has-text("Reject all")', 'button:has-text("Accept All")',
                'button:has-text("Accept all")', 'button:has-text("Agree")',
                'button:has-text("OK")', '[data-testid="uc-deny-all-button"]',
                '[data-testid="uc-accept-all-button"]', '#usercentrics-root button'):
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=2500)
            loc.click(); page.wait_for_timeout(700)
            print("  login: dismissed cookie-consent banner")
            return True
        except Exception:
            continue
    return False


def login(page):
    email, password = _login_creds()
    if not email or not password:
        raise RuntimeError("DISH login failed — DISH_EMAIL or DISH_PASSWORD is empty on Render")
    print("  login: using %s (password len=%d)" % (email, len(password)))
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    settle(page, 2000)
    _dismiss_consent(page)

    if not _angular_fill(page, [
        '#username', 'input#username', '[formcontrolname="username"]',
        'input[placeholder="Your email address"]',
    ], email, label="email"):
        _login_debug_shot(page, "email_fail")
        raise RuntimeError("DISH login failed — could not fill email field")

    if not _click_continue(page):
        raise RuntimeError("DISH login failed — Continue button not found (email step)")

    try:
        _wait_password_visible(page, timeout_ms=20000)
    except Exception:
        _login_debug_shot(page, "no_password_field")
        raise RuntimeError("DISH login failed — password field never appeared after email")

    page.wait_for_timeout(800)
    _dismiss_consent(page)

    if not _angular_fill(page, [
        '#password', 'input#password', '[formcontrolname="password"]',
        'input[type="password"]', 'input[placeholder="Your password"]',
    ], password, label="password"):
        _login_debug_shot(page, "password_fail")
        raise RuntimeError("DISH login failed — could not fill password field")

    # DISH uses the same Continue button for both steps (not "Log in").
    submitted = False
    for method in ("continue", "enter"):
        try:
            if method == "continue":
                _click_continue(page)
            else:
                page.locator('#password').first.press("Enter")
            page.wait_for_load_state("domcontentloaded", timeout=20000)
            page.wait_for_timeout(1500)
            if _wait_logged_in(page, timeout_ms=25000):
                submitted = True
                break
        except Exception as e:
            print("  login: submit via %s: %s" % (method, str(e)[:90]))

    if not submitted:
        err = _login_error_text(page)
        _login_debug_shot(page, "fail")
        hint = (" — %s" % err) if err else " — check DISH_EMAIL and DISH_PASSWORD on Render (no extra quotes)"
        raise RuntimeError("DISH login failed%s" % hint)


def run_actions(page, actions, V, shots):
    for a in actions:
        try:
            if "goto" in a:
                page.goto(URLS.get(a["goto"], a["goto"]), wait_until="domcontentloaded"); settle(page, a.get("settle", 2400))
            elif "click" in a:
                _cl = [_vars(s, V) for s in (a["click"] if isinstance(a["click"], list) else [a["click"]])]
                try_each(page, "click", _cl, t=a.get("t", 3000))
            elif "drag" in a:
                _src = [_vars(s, V) for s in (a["drag"] if isinstance(a["drag"], list) else [a["drag"]])]
                _dst = [_vars(s, V) for s in (a.get("to", []) if isinstance(a.get("to", []), list) else [a.get("to")])]
                drag_drop(page, _src, _dst, t=a.get("t", 3000))
            elif "dump" in a:
                dump_dom(page, a["dump"])
            elif "fill" in a:
                try_each(page, "fill", a["fill"], value=_vars(a["value"], V), t=a.get("t", 3000))
            elif "tick_each" in a:
                # Tick the checkbox for EACH named item (e.g. allergens "Gluten, Milk, Sesame").
                items = [x.strip() for x in _vars(a["tick_each"], V).split(",") if x.strip()]
                for it in items:
                    sels = [
                        'app-check-box:has-text("%s") input' % it,
                        'app-check-box:has-text("%s") .p-checkbox-box' % it,
                        'app-check-box:has-text("%s")' % it,
                        'label:has-text("%s") input[type="checkbox"]' % it,
                        'input[type="checkbox"]:right-of(:text-is("%s"))' % it,
                        ':text-is("%s")' % it,
                    ]
                    try_each(page, "click", sels, t=1500)
                    page.wait_for_timeout(300)
            elif "assert_found" in a:
                # After a search, confirm a row actually matches the product. If not, the
                # product isn't in the catalogue, so we stop and let the build reply smartly
                # instead of silently editing the wrong (first) row.
                name = _vars(a["assert_found"], V)
                rowsel = a.get("rows", "tbody tr")
                found = False
                try:
                    rows = page.locator(rowsel); cnt = min(rows.count(), 12)
                    for i in range(cnt):
                        if name.lower() in (rows.nth(i).inner_text(timeout=1500) or "").lower():
                            found = True; break
                except Exception:
                    found = True   # never block the build on a checker error
                if not found:
                    raise RuntimeError("PRODUCT_NOT_FOUND:%s" % name)
            elif "tick_each" in a:
                # Tick a checkbox for each item in a comma list (e.g. {ALLERGENS}="Milk, Gluten").
                # Best-effort: tries several selector shapes per item, never fails the build.
                items = [x.strip() for x in _vars(a["tick_each"], V).split(",") if x.strip()]
                tmpls = a.get("selector", [
                    "app-check-box:has-text(\"{item}\") input",
                    "label:has-text(\"{item}\") input[type=\"checkbox\"]",
                    "*:has(> input[type=\"checkbox\"]):has-text(\"{item}\") input",
                    "input[type=\"checkbox\"]:near(:text(\"{item}\"))",
                ])
                if not isinstance(tmpls, list): tmpls = [tmpls]
                for it in items:
                    sels = [t.replace("{item}", it) for t in tmpls]
                    if not try_each(page, "check", sels, t=2000):
                        try_each(page, "click", ["app-check-box:has-text(\"%s\")" % it,
                                                 "label:has-text(\"%s\")" % it,
                                                 ":text-is(\"%s\")" % it], t=1500)
                    page.wait_for_timeout(250)
            elif "key" in a:
                page.keyboard.press(a["key"])
            elif "dropdown" in a:
                dropdown_pick(page, a["dropdown"], a.get("pick", []))
            elif "select" in a:
                select_field(page, _vars(a["select"], V), [_vars(p, V) for p in a.get("pick", [])])
            elif "scrollto" in a:
                for sel in (a["scrollto"] if isinstance(a["scrollto"], list) else [a["scrollto"]]):
                    try: page.locator(_vars(sel, V)).first.scroll_into_view_if_needed(timeout=2500); break
                    except Exception: continue
                page.wait_for_timeout(a.get("t", 600))
            elif "wait" in a:
                page.wait_for_timeout(a["wait"])
            elif "settle" in a:
                settle(page, a.get("settle", 2400))
            elif "snap" in a:
                step = a["snap"]; path = a["_ssdir"] / ("step_%02d.png" % step)
                try: page.screenshot(path=str(path))
                except Exception as e: print("  snap fail", step, e)
                try: rel = str(path.relative_to(ROOT)).replace("\\", "/")
                except Exception: rel = "output/screenshots/%s/%s" % (path.parent.name, path.name)
                shot = {"step": step, "screenshot": rel, "url": page.url}
                # optional: record the on-screen box of the element this step is about,
                # so the PDF/video can draw the orange iorad-style highlight on it.
                hl = a.get("highlight")
                if hl:
                    hl = [_vars(s, V) for s in (hl if isinstance(hl, list) else [hl])]
                    for sel in hl:
                        try:
                            box = page.locator(sel).first.bounding_box(timeout=1500)
                            if box and box["width"] > 0 and box["height"] > 0:
                                pad = 6
                                shot["bbox"] = [max(0, round(box["x"]-pad)), max(0, round(box["y"]-pad)),
                                                round(box["width"]+2*pad), round(box["height"]+2*pad)]
                                # LEARN: remember which selector worked for this semantic target
                                if a.get("target"):
                                    try:
                                        from intelligence import resolver
                                        resolver.record_success(a["target"], sel, page.url)
                                    except Exception: pass
                                break
                        except Exception:
                            continue
                # MODEL FALLBACK (accurate): selectors missed -> let GPT PICK the right control
                # from the page's real elements; we use that element's EXACT box (Playwright),
                # never guessed coordinates. GPT is the brain; the browser supplies the geometry.
                if hl and not shot.get("bbox"):
                    try:
                        from intelligence import llm, resolver
                        hint = a.get("vhint") or a.get("_caption") or _vhint(hl)
                        if llm.available() and hint:
                            cands = page.evaluate(_CANDS_JS)
                            idx = resolver.pick_element(hint, cands)
                            if idx is not None:
                                c = cands[idx]; pad = 4
                                box = [max(0, round(c["x"]-pad)), max(0, round(c["y"]-pad)),
                                       round(c["w"]+2*pad), round(c["h"]+2*pad)]
                                # SELF-CHECK the pick: crop that region and ask the model to
                                # confirm. A bad pick becomes NO box (safe), not a WRONG box.
                                keep = True
                                try:
                                    from PIL import Image
                                    crop = Image.open(str(path)).crop(
                                        (box[0], box[1], box[0]+box[2], box[1]+box[3]))
                                    tmp = path.with_suffix(".crop.png")
                                    crop.save(str(tmp))
                                    chk = llm.ask_vision("Does this cropped UI region show %s? "
                                                         "Answer YES or NO." % hint, str(tmp))
                                    tmp.unlink()
                                    keep = bool(chk) and chk.strip().upper().startswith("Y")
                                except Exception:
                                    keep = True
                                if keep:
                                    shot["bbox"] = box; shot["bbox_src"] = "model-pick"
                                    print("  step %02d highlight chosen by model: %s" % (step, (c.get("text") or "")[:30]))
                                else:
                                    print("  step %02d model-pick rejected by self-check (left un-boxed)" % step)
                    except Exception as e:
                        print("  model-pick warn:", str(e)[:80])
                shots.append(shot)
                print("  captured step %02d%s" % (step, " [+highlight]" if shot.get("bbox") else "")); sys.stdout.flush()
        except Exception as e:
            if "PRODUCT_NOT_FOUND" in str(e):
                raise           # let the build stop and reply smartly
            print("  action warn:", str(e)[:110]); sys.stdout.flush()

def _load_composed(guides, extra_vars):
    """Compose one or more guide recipes into ONE continuous action list, with snap numbers
    renumbered into a single sequence. A single guide behaves exactly as before (offset 0).
    A merged question (e.g. [1, 6]) becomes one flow: add product -> menu -> (same session,
    same product) allergens. Nothing is hard-coded: product details flow through V."""
    actions, caps, titles = [], {}, []
    V, offset = {}, 0
    for g in guides:
        rec = json.loads((ROOT / "recipes" / ("Q%02d_capture.json" % g)).read_text(encoding="utf-8"))
        V.update(rec.get("vars", {}))
        try:
            sc = json.loads((ROOT / "recipes" / ("Q%02d_script.json" % g)).read_text(encoding="utf-8"))
            gcaps = {s["step"]: s.get("caption", "") for s in sc.get("steps", [])}
            nsteps = max([s["step"] for s in sc.get("steps", [])] or [0])
            titles.append(sc.get("workflow_title", rec.get("workflow_title", "")))
        except Exception:
            gcaps = {}; nsteps = max([a["snap"] for a in rec["actions"] if "snap" in a] or [0])
            titles.append(rec.get("workflow_title", ""))
        for a in rec["actions"]:
            a2 = dict(a)
            if "snap" in a2:
                a2["snap"] = a2["snap"] + offset
                caps[a2["snap"]] = gcaps.get(a["snap"], "")
            actions.append(a2)
        offset += nsteps
    if extra_vars:
        V.update({k: v for k, v in extra_vars.items() if v})
    return actions, V, caps, guides[0], " + ".join([t for t in titles if t]), (len(guides) > 1)

def main(qid=1, headless=False, slowmo=250, extra_vars=None, guides=None):
    _NOT_FOUND.clear()
    guides = guides or [qid]
    actions, V, caps, primary, wf_title, composite = _load_composed(guides, extra_vars)
    if extra_vars:
        print("ENGINE: using custom vars %s" % {k: V[k] for k in extra_vars if k in V})
    if composite:
        SS = ROOT / "output" / "screenshots" / ("q%02d_combined" % primary); SS.mkdir(parents=True, exist_ok=True)
        man_path = ROOT / "output" / ("manifest_q%02d_combined.json" % primary)
    else:
        SS = ss_dir(primary); man_path = manifest_path(primary)
    for a in actions:
        a["_ssdir"] = SS
        if "snap" in a and caps.get(a["snap"]):
            a["_caption"] = caps[a["snap"]]
    shots = []
    label = ("+".join("Q%02d" % g for g in guides)) if composite else ("Q%02d" % primary)
    print("ENGINE: live capture for %s (%s)%s" % (label, wf_title,
          " [one continuous session]" if composite else "")); sys.stdout.flush()
    with sync_playwright() as p:
        b = launch_chromium(p, headless=headless, slow_mo=slowmo)
        page = new_browser_page(b)
        try:
            login(page)
            run_actions(page, actions, V, shots)
            print("ENGINE: capture finished (%d shots)" % len(shots))
        except Exception as e:
            if "PRODUCT_NOT_FOUND" in str(e):
                _NOT_FOUND["name"] = str(e).split("PRODUCT_NOT_FOUND:", 1)[-1].strip()
            else:
                print("ENGINE stopped:", str(e)[:160])
        finally:
            shots.sort(key=lambda s: s["step"])
            man_path.write_text(json.dumps({
                "qid": primary, "guides": guides, "workflow_title": wf_title,
                "recorded_at": datetime.now(timezone.utc).isoformat(), "screenshots": shots}, indent=2))
            print("manifest ->", man_path, "(%d steps)" % len(shots))
            page.wait_for_timeout(500); b.close()
    if _NOT_FOUND.get("name"):
        print("PRODUCT_NOT_FOUND: %s (no guide produced)" % _NOT_FOUND["name"])
    return dict(_NOT_FOUND)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--qid", type=int, default=1); ap.add_argument("--headless", action="store_true")
    ap.add_argument("--slowmo", type=int, default=250)
    a = ap.parse_args(); main(qid=a.qid, headless=a.headless, slowmo=a.slowmo)
