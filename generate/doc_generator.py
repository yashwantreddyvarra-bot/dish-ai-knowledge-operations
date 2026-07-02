# generate/doc_generator.py - Layer 2: branded PDF + video for ANY question (by qid).
import sys, json, textwrap, re
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config.settings import DOCS_DIR, VIDEO_DIR

def _slug(s):
    """Filesystem-safe short slug for adhoc (random-question) output filenames."""
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:30] or "item"

def _paths(qid):
    return {
        "script":   ROOT / "recipes" / ("Q%02d_script.json" % qid),
        "manifest": ROOT / "output" / ("manifest_q%02d.json" % qid),
        "enriched": ROOT / "output" / ("manifest_q%02d_enriched.json" % qid),
        "pdf_ts":   lambda ts: Path(DOCS_DIR) / ("Q%02d_branded_%s.pdf" % (qid, ts)),
        "mp4":      Path(VIDEO_DIR) / ("Q%02d_walkthrough.mp4" % qid),
        "gif":      Path(VIDEO_DIR) / ("Q%02d_walkthrough.gif" % qid),
        "frames":   ROOT / "output" / "vframes" / ("q%02d" % qid),
    }

def _read_json(p):
    try: return json.JSONDecoder().raw_decode(Path(p).read_text(encoding="utf-8"))[0]
    except Exception: return None

def _source_note(manifest):
    urls = [s.get("url", "") for s in manifest.get("screenshots", [])]
    live = any(u.startswith("http") for u in urls)
    if live:
        host = urlparse(next(u for u in urls if u.startswith("http"))).netloc
        return ("LIVE capture - %s from %s" % (datetime.now().strftime("%Y-%m-%d %H:%M"), host)), True
    return "DEMO - reference screenshots (run capture for a live version)", False

def _resolve(img_path, qid):
    """Find the screenshot regardless of how its path was stored (Win/Linux/relative)."""
    if not img_path: return None
    if Path(img_path).exists(): return img_path
    name = Path(str(img_path).replace("\\", "/")).name          # bare filename
    for cand in (ROOT/"output"/"screenshots"/("q%02d" % qid)/name,
                 ROOT/"output"/"screenshots"/name):
        if cand.exists(): return str(cand)
    return None

def _shots(manifest, qid):
    out = {}
    for s in manifest.get("screenshots", []):
        rp = _resolve(s.get("screenshot"), qid)
        if rp: out[s["step"]] = rp
    return out

def build(qid, vars=None, adhoc=False):
    # adhoc=True  -> a random/free-text question with a custom product. The output is a
    #   throw-away PREVIEW: it is written with a distinct "_adhoc_" filename and NEVER
    #   deletes or overwrites the canonical Q01-25 "_branded_" guide. Returns its path.
    # adhoc=False -> a canonical guide build (the saved 25); keeps the newest, prunes stale.
    P = _paths(qid)
    script = _read_json(P["script"])
    manifest = _read_json(P["manifest"]) or {"screenshots": []}
    if not script:
        print("No script for Q%02d" % qid); return None
    # Substitute product placeholders ({NAME}/{PRICE}) in the captions so a tailored build
    # shows the user's product in the TEXT too (defaults come from the recipe's vars, so a
    # normal build still reads naturally).
    V = {}
    rec = _read_json(ROOT / "recipes" / ("Q%02d_capture.json" % qid))
    if rec:
        V.update(rec.get("vars", {}))
    if vars:
        V.update({k: v for k, v in vars.items() if v})
    if V:
        for st in script["steps"]:
            c = st.get("caption", "")
            for k, val in V.items():
                c = c.replace("{%s}" % k, str(val))
            st["caption"] = c
    note, live = _source_note(manifest)
    print("Q%02d source: %s" % (qid, note))
    shots = _shots(manifest, qid)
    # carry the iorad-style highlight box (recorded at capture time) onto the script steps
    bbox_map = {s["step"]: s.get("bbox") for s in manifest.get("screenshots", []) if s.get("bbox")}
    for st in script["steps"]:
        if bbox_map.get(st["step"]): st["bbox"] = bbox_map[st["step"]]
    cap = {s["step"]: s["caption"] for s in script["steps"]}
    enr = dict(manifest); enr["workflow_title"] = script.get("workflow_title", "")
    for s in enr.get("screenshots", []):
        s["llm_caption"] = cap.get(s["step"], ""); s["label"] = cap.get(s["step"], "")
    P["enriched"].write_text(json.dumps(enr, indent=2), encoding="utf-8")
    from generate.branded_pdf import build_branded_pdf
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slug(V.get("NAME") or "item")
    out = (Path(DOCS_DIR) / ("Q%02d_adhoc_%s_%s.pdf" % (qid, slug, ts))) if adhoc else P["pdf_ts"](ts)
    build_branded_pdf(script, shots, out, source_note=note, live=live)
    filled = sum(1 for st in script["steps"] if st["step"] in shots)
    print("Q%02d branded PDF -> %s   [%s, %d/%d pages]" % (qid, out, "LIVE" if live else "DEMO", filled, len(script["steps"])))
    if filled == 0:
        # Screenshots are missing on disk (manifest points at deleted/moved files).
        # Do NOT delete the previous good PDF in favour of this empty one, and warn loudly.
        print("Q%02d WARNING: 0/%d screenshots resolved - the capture output is missing. "
              "Re-run live capture (run_capture.bat %d) to regenerate screenshots. "
              "Keeping any earlier PDF; not building video from blank frames." %
              (qid, len(script["steps"]), qid))
        try: out.unlink()      # drop the just-written blank PDF
        except Exception: pass
        return None
    # Canonical builds keep ONLY the newest "_branded_" PDF (prune stale). Adhoc/random
    # previews never touch the canonical guide files.
    if not adhoc:
        for old_pdf in Path(DOCS_DIR).glob("Q%02d_branded_*.pdf" % qid):
            if old_pdf != out:
                try: old_pdf.unlink()
                except Exception: pass
    _build_video(qid, script, shots, note, P, ts, adhoc=adhoc, slug=slug)
    return out

def build_combined(guides, vars=None, adhoc=True):
    """Build ONE continuous PDF + video from a composed multi-guide capture
    (manifest_q{primary}_combined.json). Captions from each guide's script are concatenated
    and renumbered 1..N, matched to the combined manifest's renumbered screenshots. This is
    what makes a merged question (e.g. add-to-menu + allergens) a single continuous guide."""
    primary = guides[0]
    man = _read_json(ROOT / "output" / ("manifest_q%02d_combined.json" % primary)) or {"screenshots": []}
    V = {}
    for g in guides:
        rec = _read_json(ROOT / "recipes" / ("Q%02d_capture.json" % g))
        if rec:
            V.update(rec.get("vars", {}))
    if vars:
        V.update({k: v for k, v in vars.items() if v})
    steps, titles, n = [], [], 1
    for gi, g in enumerate(guides):
        sc = _read_json(ROOT / "recipes" / ("Q%02d_script.json" % g))
        if not sc:
            continue
        titles.append(sc.get("workflow_title", ""))
        for si, st in enumerate(sc.get("steps", [])):
            cap = st.get("caption", "")
            for k, val in V.items():
                cap = cap.replace("{%s}" % k, str(val))
            if gi > 0 and si == 0:                       # mark where the next sub-task begins
                cap = "Next — %s. %s" % (sc.get("workflow_title", ""), cap)
            steps.append({"step": n, "caption": cap, "action": st.get("action", "")})
            n += 1
    if not steps:
        print("combined: no steps"); return None
    script = {"workflow_title": " + ".join([t for t in titles if t]), "steps": steps}
    shots = _shots(man, primary)
    bbox_map = {s["step"]: s.get("bbox") for s in man.get("screenshots", []) if s.get("bbox")}
    for st in steps:
        if bbox_map.get(st["step"]):
            st["bbox"] = bbox_map[st["step"]]
    note, live = _source_note(man)
    print("Q%02d combined source: %s" % (primary, note))
    from generate.branded_pdf import build_branded_pdf
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slug(V.get("NAME") or "item")
    tag = "+".join("Q%02d" % g for g in guides)
    out = (Path(DOCS_DIR) / ("Q%02d_adhoc_%s_full_%s.pdf" % (primary, slug, ts))) if adhoc \
          else (Path(DOCS_DIR) / ("Q%02d_full_%s.pdf" % (primary, ts)))
    build_branded_pdf(script, shots, out, source_note=note, live=live)
    filled = sum(1 for st in steps if st["step"] in shots)
    print("Combined PDF (%s) -> %s   [%d/%d pages]" % (tag, out, filled, len(steps)))
    if filled == 0:
        try: out.unlink()
        except Exception: pass
        return None
    _build_video(primary, script, shots, note, _paths(primary), ts, adhoc=adhoc, slug=slug + "_full")
    return out

def _load_img(Image, p):
    """Load a screenshot tolerantly: PIL first, then imageio (handles odd PNGs)."""
    if not p or not Path(p).exists(): return None
    try:
        im = Image.open(p); im.load(); return im.convert("RGB")
    except Exception:
        pass
    try:
        import imageio.v3 as iio
        return Image.fromarray(iio.imread(p)).convert("RGB")
    except Exception:
        return None

def _compose_frame(Image, ImageDraw, ImageFont, st, img_path, note, W, H, hdr, font, capfont, small):
    """One video frame: title banner + wrapped caption + aspect-correct screenshot."""
    cv = Image.new("RGB", (W, H), (245, 246, 248))
    d = ImageDraw.Draw(cv)
    # orange banner
    d.rectangle([0, 0, W, hdr], fill=(230, 92, 38))
    d.text((28, 16), "DISH POS  -  Step %d" % st["step"], fill="white", font=font)
    d.text((W-470, 20), note, fill=(255, 235, 220), font=small)
    # caption (wrapped, up to 2 lines)
    lines = textwrap.wrap(st["caption"], 100)[:3]
    for i, ln in enumerate(lines):
        d.text((28, hdr + 14 + i*30), ln, fill=(29, 32, 39), font=capfont)
    # screenshot area (preserve aspect ratio, letterbox)
    top = hdr + 14 + len(lines)*30 + 16
    area = (W-56, H-top-24)
    im = _load_img(Image, img_path)
    if im is not None:
        try:
            r = min(area[0]/im.width, area[1]/im.height)
            nw, nh = int(im.width*r), int(im.height*r)
            ox, oy = (area[0]-nw)//2, (area[1]-nh)//2
            box = Image.new("RGB", area, (255, 255, 255))
            box.paste(im.resize((nw, nh)), (ox, oy))
            cv.paste(box, (28, top))
            # iorad-style orange highlight on the clicked element
            bb = st.get("bbox")
            if bb and len(bb) == 4:
                bx = 28 + ox + bb[0]*r; by = top + oy + bb[1]*r
                bd = ImageDraw.Draw(cv)
                for o in range(3):
                    bd.rectangle([bx-o, by-o, bx+bb[2]*r+o, by+bb[3]*r+o], outline=(236, 106, 56))
        except Exception:
            d.text((W//2-170, top+area[1]//2), "screenshot pending capture", fill=(150,150,150), font=capfont)
    else:
        d.text((W//2-170, top+area[1]//2), "screenshot pending capture", fill=(150,150,150), font=capfont)
    return cv

def _build_video(qid, script, shots, note, P, ts="", seconds_per_step=2.8, fps=10, adhoc=False, slug=""):
    from PIL import Image, ImageDraw, ImageFont, ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    import imageio, numpy as np, glob as _glob, os as _os
    ts = ts or datetime.now().strftime("%Y%m%d_%H%M%S")
    # adhoc previews get a distinct "_adhoc_" name and never prune canonical walkthroughs
    mp4 = (Path(VIDEO_DIR) / ("Q%02d_adhoc_%s_%s.mp4" % (qid, slug or "item", ts))) if adhoc \
          else (Path(VIDEO_DIR) / ("Q%02d_walkthrough_%s.mp4" % (qid, ts)))   # unique per build (no stale cache)
    W, H, hdr = 1440, 900, 70
    def _f(sz):
        for name in ("arial.ttf", "DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"):
            try: return ImageFont.truetype(name, sz)
            except Exception: continue
        return ImageFont.load_default()
    font, capfont, small = _f(26), _f(22), _f(15)
    P["frames"].mkdir(parents=True, exist_ok=True)
    frames = []
    for st in script["steps"]:
        cv = _compose_frame(Image, ImageDraw, ImageFont, st, shots.get(st["step"]), note, W, H, hdr, font, capfont, small)
        cv.save(P["frames"] / ("step_%02d.png" % st["step"]))   # verifiable still
        arr = np.array(cv)
        for _ in range(int(seconds_per_step*fps)): frames.append(arr)
    if not frames: return None
    try:
        imageio.mimsave(mp4, frames, fps=fps, codec="libx264",
                        output_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
                        macro_block_size=16, quality=8)
        print("Q%02d MP4 -> %s (%d frames)" % (qid, mp4, len(frames)))
        # keep ONLY this newest canonical walkthrough (adhoc previews never prune canonical)
        if not adhoc:
            for old in _glob.glob(str(Path(VIDEO_DIR) / ("Q%02d_walkthrough*.mp4" % qid))):
                if Path(old).resolve() != mp4.resolve():
                    try: _os.remove(old)
                    except Exception: pass
    except Exception as e: print("MP4 failed (%s)" % e)
    print("Q%02d frames dumped -> %s" % (qid, P["frames"]))

def main():
    qid = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    build(qid); print("Done Q%02d." % qid)

if __name__ == "__main__":
    main()
