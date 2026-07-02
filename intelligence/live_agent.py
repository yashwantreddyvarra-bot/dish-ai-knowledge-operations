"""live_agent.py - LIVE LLM LOOP for brand-new tasks (the typed lane's last resort).

When a typed question matches NO recipe, this drives the sandbox click-by-click:
    look (screenshot + read the page's real elements) -> the model picks ONE next action
    -> execute it -> look again -> ... until the model says done or a step cap is hit.

It reuses the proven capture-engine plumbing (login, settle, the element-reader, the
model element-picker) so the browser supplies real geometry and the model is only the brain.

SAFETY (non-negotiable, enforced here):
  * SANDBOX ONLY - refuses to run if the login URL is not the sandbox host.
  * DESTRUCTIVE CLICKS BLOCKED - never clicks delete / remove / confirm / pay / submit / send.
  * HARD STEP CAP - cannot loop forever.
Its screenshots feed the same builder + CONFIDENCE GATE; an unsure result is flagged for a
human and is never auto-published. Experimental: proven only on simple tasks so far.
"""
import json, re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"

# Words that mark an irreversible / money / data-destructive control - never auto-clicked.
BLOCK = ("delete", "remove", "confirm", "pay", "purchase", "checkout", "submit",
         "send", "publish", "deactivate", "cancel subscription", "empty trash",
         "permanently", "wipe", "reset")

_DECIDE = (
    "You are operating the DISH POS Backoffice (a sandbox) to accomplish a task, one click "
    "at a time. TASK: \"%s\".\n\nSteps done so far:\n%s\n\nThe page right now exposes these "
    "interactive elements (index: text/role):\n%s\n\nChoose the SINGLE next action. Reply with "
    "STRICT JSON only:\n{\"action\":\"click\"|\"fill\"|\"done\",\"index\":<element index or null>,"
    "\"value\":\"<text to type, for fill>\",\"caption\":\"<one short sentence describing this step>\"}\n"
    "Use \"done\" when the task is complete. Never choose a destructive control."
)


def _is_sandbox():
    try:
        from capture.engine import LOGIN_URL
        return "sandbox" in (LOGIN_URL or "").lower()
    except Exception:
        return False


def _blocked(text):
    t = (text or "").lower()
    return any(b in t for b in BLOCK)


def _selectors_for(cand):
    """Best-effort, replayable selectors for a chosen element (used ONLY if the run is
    later promoted into a recipe). Live driving itself uses the element's real geometry."""
    t = (cand.get("text") or "").strip().splitlines()[0][:40].replace('"', "'") if cand else ""
    role = (cand.get("role") or "").lower()
    sels = []
    if t:
        sels += ['button:has-text("%s")' % t, 'a:has-text("%s")' % t,
                 '[role="button"]:has-text("%s")' % t, 'text=%s' % t]
    if role in ("input", "textbox", "combobox", "mat-select", "select"):
        sels += ['input', 'textarea']
    return sels or ["body"]


def solve(task, qid=99, max_steps=12, headless=False):
    """Drive the sandbox to attempt `task`. Returns a manifest dict (screenshots + captions)
    for the builder, or {'error': ...}. Never runs off-sandbox; never clicks destructive controls."""
    if not _is_sandbox():
        return {"error": "refused: live agent runs on the sandbox only"}
    from capture import engine
    from intelligence import llm
    if not llm.available():
        return {"error": "live agent needs a model (LLM) and none is configured"}

    ssdir = OUT / "screenshots" / ("q%02d_live" % qid); ssdir.mkdir(parents=True, exist_ok=True)
    shots, captions, history, actions = [], [], [], []
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=headless, slow_mo=250)
        page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.set_default_timeout(8000)
        try:
            engine.login(page)
            for step in range(1, max_steps + 1):
                engine.settle(page, 1500)
                shot = ssdir / ("step_%02d.png" % step)
                try: page.screenshot(path=str(shot))
                except Exception: pass
                cands = []
                try: cands = page.evaluate(engine._CANDS_JS)
                except Exception: pass
                listing = "\n".join("%d: %s [%s]" % (i, (c.get("text") or "")[:50], c.get("role", ""))
                                    for i, c in enumerate(cands[:40]))
                raw = llm.ask_text(_DECIDE % (task, "\n".join(history) or "(none yet)", listing),
                                   system="You output only strict JSON.", max_tokens=300)
                m = re.search(r"\{.*\}", raw or "", re.S)
                if not m:
                    break
                try: act = json.loads(m.group(0))
                except Exception: break
                a = (act.get("action") or "").lower()
                cap = act.get("caption") or ("Step %d" % step)
                idx = act.get("index")
                shots.append({"step": step, "screenshot": "output/screenshots/q%02d_live/step_%02d.png" % (qid, step),
                              "url": page.url})
                captions.append(cap); history.append("%d. %s" % (step, cap))

                valid = isinstance(idx, int) and 0 <= idx < len(cands)
                target = cands[idx] if valid else None
                will_block = bool(target and _blocked(target.get("text")))

                # Record a REPLAYABLE recipe action for this step. Used only if the run is
                # later promoted; one snap per step keeps it aligned with the caption script.
                if a == "done" or not valid or will_block:
                    actions.append({"snap": step})
                else:
                    sels = _selectors_for(target)
                    if a == "fill" and act.get("value"):
                        actions.append({"fill": sels, "value": str(act["value"])})
                        actions.append({"snap": step, "highlight": sels})
                    else:
                        actions.append({"click": sels, "t": 2500})
                        actions.append({"wait": 700})
                        actions.append({"snap": step, "highlight": sels})

                if a == "done":
                    break
                if not valid:
                    continue
                if will_block:
                    history.append("(blocked a destructive control: %s)" % (target.get("text") or "")[:30])
                    continue
                try:
                    x = target["x"] + target.get("w", 0) / 2; y = target["y"] + target.get("h", 0) / 2
                    if a == "fill" and act.get("value"):
                        page.mouse.click(x, y); page.keyboard.type(str(act["value"]))
                    else:
                        page.mouse.click(x, y)
                except Exception as e:
                    history.append("(action failed: %s)" % str(e)[:50])
        except Exception as e:
            return {"error": "live agent stopped: %s" % str(e)[:160]}
        finally:
            try: b.close()
            except Exception: pass

    man = {"qid": qid, "guides": [qid], "workflow_title": task,
           "recorded_at": datetime.now(timezone.utc).isoformat(), "screenshots": shots,
           "captions": captions, "actions": actions, "live_agent": True}
    (OUT / ("manifest_q%02d_live.json" % qid)).write_text(json.dumps(man, indent=2), encoding="utf-8")
    return man
