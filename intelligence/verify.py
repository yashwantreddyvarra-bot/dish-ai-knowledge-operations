"""
verify.py - VERIFY: self-check every built tutorial and score REAL quality.

What counts against the score (these are genuine defects):
  - a step with no screenshot / a blank frame / a frame that didn't render   -> FAIL
  - (with a model) the orange highlight box is on the WRONG element           -> FAIL
  - (with a model) the screenshot shows the wrong screen for the caption      -> WARN

What does NOT count against the score (these are not defects):
  - a step with no highlight box (the locator legitimately declined)         -> note only
  - a step whose screen is the same as the previous step (form walkthroughs) -> note only

Key idea: the rendered video frame already has the orange box drawn on it, so for steps that
HAVE a box we ask gpt-4o "is the box on the correct element for this instruction?" - that
judges PLACEMENT, not mere presence. So a wrong box now scores LOWER than an honest no-box,
and the number finally means "did it get the right thing".
"""
import json, hashlib, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
try:
    from config.settings import VIDEO_DIR
except Exception:
    VIDEO_DIR = OUT / "videos"


def _read(p):
    try:
        return json.JSONDecoder().raw_decode(Path(p).read_text(encoding="utf-8"))[0]
    except Exception:
        return None


def _frame_stats(path):
    try:
        from PIL import Image, ImageFile
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        im = Image.open(path).convert("L").resize((16, 16))
        px = list(im.getdata())
        avg = sum(px) / len(px)
        bits = "".join("1" if p > avg else "0" for p in px)
        var = sum((p - avg) ** 2 for p in px) / len(px)
        return (var < 25, hashlib.md5(bits.encode()).hexdigest())
    except Exception:
        return (True, None)


def _score(qid, script, manifest, frames_dir, mp4, use_vision=True):
    shots = {s["step"]: s for s in manifest.get("screenshots", [])}

    from . import llm
    vision = use_vision and llm.available()
    steps_out, prev_hash, _vfail = [], None, 0
    for st in script["steps"]:
        n = st["step"]
        rec = {"step": n, "status": "ok", "issues": [], "notes": []}
        shot = shots.get(n)
        fp = frames_dir / ("step_%02d.png" % n)

        # hard defects (always scored)
        if not shot or not shot.get("screenshot"):
            rec["status"] = "fail"; rec["issues"].append("no screenshot captured")
        if fp.exists():
            blank, h = _frame_stats(fp)
            if blank:
                rec["status"] = "fail"; rec["issues"].append("frame looks blank")
            if h and h == prev_hash:
                rec["notes"].append("same screen as previous step (ok for form walkthroughs)")
            prev_hash = h
        else:
            rec["status"] = "fail"; rec["issues"].append("frame not rendered")

        has_box = bool(shot and shot.get("bbox"))
        if not has_box and st.get("action") == "click" and st.get("highlight"):
            rec["notes"].append("no highlight box (locator declined - not penalised)")

        # An intro / "welcome" step is general context, not a specific screen to match,
        # so don't penalise its screenshot for "not matching" (only judge it if it has a box).
        is_info = (st.get("action") == "info"
                   or (st.get("caption", "").lower().lstrip().startswith("welcome")))
        # semantic check with the model: judge PLACEMENT when there is a box
        if vision and fp.exists() and rec["status"] != "fail" and not (is_info and not has_box):
            if has_box:
                q = ("An orange highlight box has been drawn on this DISH POS screenshot to "
                     "mark the element for the instruction: \"%s\". Is the orange box on the "
                     "CORRECT element? Answer YES or NO and a short reason." % st["caption"])
            else:
                q = ("Does this DISH POS screenshot show the correct screen/state for the "
                     "instruction: \"%s\"? Answer YES or NO and a short reason." % st["caption"])
            ans = llm.ask_vision(q, str(fp))
            if ans:
                _vfail = 0
                rec["vision"] = ans.strip()[:170]
                if ans.strip().upper().startswith("NO"):
                    if has_box:
                        rec["status"] = "fail"; rec["issues"].append("vision: box on wrong element")
                    else:
                        rec["status"] = "warn" if rec["status"] == "ok" else rec["status"]
                        rec["issues"].append("vision: screen mismatch")
            else:
                # model didn't answer (bad key / offline / timed out) -> fail fast: after 2 misses,
                # stop calling vision for the rest of this build so it can't crawl or hang.
                _vfail += 1
                if _vfail >= 2:
                    vision = False
                    print("Q%02d verify: vision model not responding - grading the rest with heuristics" % qid)
        steps_out.append(rec)

    total = len(steps_out) or 1

    def has(s, *keys):
        return any(any(k in i for k in keys) for i in s["issues"])

    # categorise defects by what they actually damage
    render_bad = sum(1 for s in steps_out if has(s, "no screenshot", "blank", "not rendered"))
    box_bad    = sum(1 for s in steps_out if has(s, "box on wrong element"))
    screen_bad = sum(1 for s in steps_out if has(s, "screen mismatch"))
    cap_bad    = sum(1 for st in script["steps"] if not (st.get("caption") or "").strip())

    # video-only health: file present + a frame per step
    nframes = len(glob.glob(str(frames_dir / "step_*.png")))
    frame_gap = max(0, len(steps_out) - nframes)

    # three distinct scores
    pdf_score   = round(100 * (total - render_bad - box_bad) / total)
    steps_score = round(100 * (total - screen_bad - cap_bad) / total)
    if not (mp4 and Path(mp4).exists()):
        video_score = 0
    else:
        video_score = round(100 * (total - render_bad - box_bad - frame_gap) / total)
    pdf_score = max(0, min(100, pdf_score))
    steps_score = max(0, min(100, steps_score))
    video_score = max(0, min(100, video_score))
    overall = round((pdf_score + video_score + steps_score) / 3)

    n_fail = sum(1 for s in steps_out if s["status"] == "fail")
    n_warn = sum(1 for s in steps_out if s["status"] == "warn")
    report = {"qid": qid, "vision_used": vision, "total": len(steps_out),
              "fail": n_fail, "warn": n_warn,
              "pdf_score": pdf_score, "video_score": video_score, "steps_score": steps_score,
              "score": overall, "steps": steps_out}
    (OUT / ("verify_q%02d.json" % qid)).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Q%02d verify: overall %d/100  | PDF %d  Video %d  Steps %d  (%d fail, %d warn)%s" %
          (qid, overall, pdf_score, video_score, steps_score, n_fail, n_warn,
           "  [vision]" if vision else "  [heuristic]"))
    for s in steps_out:
        if s["status"] != "ok":
            print("   step %02d  %s  - %s" % (s["step"], s["status"].upper(), "; ".join(s["issues"])))
    return report


def gate(report, threshold=90):
    """CONFIDENCE GATE. Decide whether a built guide can be auto-published or must go to a
    human. A guide PUBLISHES only when the checker is confident: overall score at/above the
    threshold AND no hard-failed steps. Otherwise it is held for REVIEW, listing exactly the
    steps that need a human glance (so review is targeted, not a full re-read)."""
    if not report or report.get("error"):
        return {"decision": "review", "score": 0, "confident": False,
                "flagged": [], "reason": report.get("error", "no report") if report else "no report"}
    score = report.get("score", 0)
    n_fail = report.get("fail", 0)
    flagged = [{"step": s["step"], "status": s["status"], "issues": s.get("issues", [])}
               for s in report.get("steps", []) if s.get("status") != "ok"]
    confident = (score >= threshold) and (n_fail == 0)
    decision = "publish" if confident else "review"
    reason = ("score %d >= %d and no failed steps" % (score, threshold) if confident
              else "score %d (need %d) / %d failed step(s)" % (score, threshold, n_fail))
    out = {"decision": decision, "score": score, "confident": confident,
           "flagged": flagged, "reason": reason, "threshold": threshold}
    print("GATE: %s - %s%s" % (decision.upper(), reason,
          ("  -> review steps %s" % [f["step"] for f in flagged]) if flagged else ""))
    return out


def question(qid, use_vision=True):
    """Score a single canonical guide (Q{qid})."""
    script = _read(ROOT / "recipes" / ("Q%02d_script.json" % qid))
    manifest = _read(OUT / ("manifest_q%02d.json" % qid)) or {"screenshots": []}
    if not script:
        return {"qid": qid, "error": "no script"}
    mp4 = Path(VIDEO_DIR) / ("Q%02d_walkthrough.mp4" % qid)
    if not mp4.exists():
        cand = glob.glob(str(Path(VIDEO_DIR) / ("Q%02d_walkthrough*.mp4" % qid)))
        if cand:
            mp4 = Path(max(cand, key=lambda p: Path(p).stat().st_mtime))
    return _score(qid, script, manifest, OUT / "vframes" / ("q%02d" % qid), mp4, use_vision)


def combined(guides, use_vision=True):
    """Score the COMBINED multi-guide walkthrough so the number reflects the SAME guide the
    PDF and video show (manifest_q{primary}_combined + the combined script captions)."""
    primary = guides[0]
    manifest = _read(OUT / ("manifest_q%02d_combined.json" % primary)) or {"screenshots": []}
    steps, n = [], 1
    for g in guides:
        sc = _read(ROOT / "recipes" / ("Q%02d_script.json" % g))
        if not sc:
            continue
        for st in sc.get("steps", []):
            steps.append({"step": n, "caption": st.get("caption", ""),
                          "action": st.get("action", ""), "highlight": st.get("highlight", "")})
            n += 1
    if not steps:
        return {"qid": primary, "error": "no script"}
    cand = glob.glob(str(Path(VIDEO_DIR) / ("Q%02d_adhoc_*_full_*.mp4" % primary)))
    mp4 = Path(max(cand, key=lambda p: Path(p).stat().st_mtime)) if cand else None
    return _score(primary, {"steps": steps}, manifest, OUT / "vframes" / ("q%02d" % primary), mp4, use_vision)


if __name__ == "__main__":
    import sys
    question(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
