# server.py - DISH Docs chatbot backend (question-aware). Run this.
import os, sys, json, re, importlib.util, threading, contextlib
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from flask import Flask, request, jsonify, render_template, send_from_directory, abort
from config.settings import BASE_OUT, DOCS_DIR, VIDEO_DIR

QUESTIONS_FILE = ROOT / "questions.json"
app = Flask(__name__, template_folder=str(ROOT / "ui" / "templates"),
            static_folder=str(ROOT / "ui" / "static"))

def _rag_ready():
    return all(importlib.util.find_spec(m) for m in ("chromadb", "sentence_transformers"))

def load_questions():
    return json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))["questions"]

def save_questions(qs):
    QUESTIONS_FILE.write_text(json.dumps({"questions": qs}, indent=2), encoding="utf-8")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/widget")
def widget():
    # Compact, responsive floating chat widget (Style A). Same-origin with the APIs,
    # so it works in a colleague's browser (laptop / monitor / phone) and inside the
    # desktop bubble launcher (desktop.py via pywebview).
    return render_template("widget.html")

@app.route("/api/questions", methods=["GET"])
def api_questions():
    return jsonify(load_questions())

@app.route("/api/questions", methods=["POST"])
def api_add_question():
    body = request.get_json(force=True)
    title = (body.get("title") or "").strip()
    if not title: return jsonify({"error": "title required"}), 400
    qs = load_questions(); new_id = max([q["id"] for q in qs], default=0) + 1
    q = {"id": new_id, "title": title, "status": "pending", "recipe": "", "pdf": "", "video": ""}
    qs.append(q); save_questions(qs); return jsonify(q)

def _has_capture(qid):
    """True only if this question has a live-capture recipe (so a build can actually run).
    New questions with step-recipes but no capture recipe yet are text-only (no failing build)."""
    try:
        return (ROOT / "recipes" / ("Q%02d_capture.json" % int(qid))).exists()
    except Exception:
        return False

@app.route("/api/question/<int:qid>")
def api_question_detail(qid):
    q = next((x for x in load_questions() if x["id"] == qid), None)
    if not q: return jsonify({"error": "not found"}), 404
    d = dict(q); d["pdf_url"] = _pdf_url(qid); d["video_url"] = _video_url(qid)
    d["buildable"] = _has_capture(qid)
    return jsonify(d)

@app.route("/api/render/<int:qid>")
def api_render(qid):
    """Render the steps for an EXACT question id (used by 'Ask about this' so the selected
    question is answered directly, never re-routed by its title text)."""
    try:
        from intelligence import agent
        full = agent.render(qid, "", polish=bool((request.args.get("polish", "1")) == "1"))
        return jsonify({"answer": full["answer"], "qid": qid, "title": full["title"],
                        "sources": full["sources"], "buildable": _has_capture(qid),
                        "pdf_url": _pdf_url(qid), "video_url": _video_url(qid),
                        "quality": _quality(qid)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _pdf_url(qid):
    pdfs = list(Path(DOCS_DIR).glob("Q%02d_branded_*.pdf" % qid))
    if not pdfs: return ""
    latest = max(pdfs, key=lambda p: p.stat().st_mtime)
    # ?v=mtime busts the browser cache whenever the file is rebuilt
    return "/files/docs/%s?v=%d" % (latest.name, int(latest.stat().st_mtime))

def _video_url(qid):
    # video filename is now unique per build (Q01_walkthrough_<ts>.mp4) - return the newest,
    # so the browser can never serve a stale clip from a previous product.
    vids = list(Path(VIDEO_DIR).glob("Q%02d_walkthrough*.mp4" % qid))
    if not vids: return ""
    latest = max(vids, key=lambda p: p.stat().st_mtime)
    return "/files/videos/%s?v=%d" % (latest.name, int(latest.stat().st_mtime))

def _quality(qid):
    """The document's evaluated quality (the verify.py /100 score), so the chatbot can
    show the user how the agent rates the guide it's handing them. Returns None if the
    doc hasn't been evaluated yet."""
    f = ROOT / "output" / ("verify_q%02d.json" % qid)
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        return {"score": d.get("score"), "fail": d.get("fail"), "warn": d.get("warn"),
                "total": d.get("total"), "pdf_score": d.get("pdf_score"),
                "video_score": d.get("video_score"), "steps_score": d.get("steps_score")}
    except Exception:
        return None

CHAT_MEMORY = __import__("collections").deque(maxlen=6)   # recent user messages (memory)

def handle_chat(msg, polish=True, chat_memory=None):
    """Core chat logic shared by Flask /api/chat and the Streamlit app. Returns a dict."""
    msg = (msg or "").strip()
    if not msg:
        return {"answer": "Ask me something about the Products section."}
    if chat_memory is None:
        chat_memory = CHAT_MEMORY
    # LONG-TERM CHAT MEMORY: remembered user facts ride along with the recent messages so
    # every answer tier can personalise; new lasting facts are extracted in the background
    # (consolidated ADD/UPDATE/DELETE - never just appended) so the chat is never slowed.
    try:
        from intelligence import memory as _mem
        history = _mem.chat_context() + list(chat_memory)
        threading.Thread(target=_mem.remember_chat, args=(msg,), daemon=True).start()
    except Exception:
        history = list(chat_memory)
    chat_memory.append(msg)

    # Classify the question's section ONCE so every routing tier stays inside it
    # (no cross-section answers). None = couldn't tell -> tiers stay unconstrained.
    section = None
    try:
        from intelligence import agent as _agent
        section = _agent.dominant_section(msg)
    except Exception:
        section = None

    # Follow-up handling: a short message that refers back ("now ... it", "also ...",
    # "only at lunch") should be understood WITH the previous turn, so route it via the
    # memory-aware GPT tier first instead of letting a single keyword grab it.
    def _is_followup(m):
        ml = m.lower().strip()
        if not history:
            return False
        if ml.startswith(("now ", "also ", "then ", "and ", "what about", "make it",
                          "set it", "only ", "just ")):
            return True
        return bool(re.search(r"\b(it|that|this|them)\b", ml)) and len(ml.split()) <= 9

    if _is_followup(msg):
        try:
            ml = msg.lower()
            time_words = ("lunch", "dinner", "breakfast", "brunch", "happy hour", "evening",
                          "morning", "during ", "only at", "certain time", "specific time",
                          "weekend", "at night")
            # "...only at lunch" -> time periods (Q17, Products). Only force it when the
            # conversation isn't clearly in another section.
            forced = 17 if (any(w in ml for w in time_words)
                            and section in (None, "Products")) else None
            qid = forced
            if not qid:
                from rag.smart_answer import answer as smart
                sm = smart(msg, history=history, section=section)
                qid = int(sm["qid"]) if sm and sm.get("qid") else None
            if qid:
                from intelligence import agent
                # A follow-up ("now make IT only at lunch") carries no product details on
                # its own - enrich the query with the recent raw messages so parameter
                # extraction still finds the product from earlier in the conversation.
                recent = [m for m in history if not m.startswith("(remembered")][-2:]
                q_ctx = " . ".join(recent + [msg]) if recent else msg
                full = agent.render(qid, q_ctx, polish=bool(polish))
                return {"answer": full["answer"], "action": "single", "qid": qid,
                        "title": full["title"], "params": full["params"], "guides": [qid],
                        "pdf_url": _pdf_url(qid), "video_url": _video_url(qid),
                        "quality": _quality(qid), "buildable": _has_capture(qid),
                        "sources": full["sources"]}
        except Exception as e:
            print("followup tier failed:", e)
    # Tier 0a: deterministic agent brain - extracts the user's product details,
    # routes to the right guide(s), merges multi-part questions, asks to clarify or
    # says when there's no guide. Always available (no network needed).
    try:
        from intelligence import agent
        ag = agent.answer(msg, polish=bool(polish))
        if ag and ag.get("answer") and ag.get("action") != "none":
            resp = {"answer": ag["answer"], "action": ag.get("action"),
                    "params": ag.get("params"), "guides": ag.get("guides", [])}
            qid = ag.get("qid")
            if qid:
                resp["qid"] = qid
                resp["title"] = ag.get("title", "")
                resp["pdf_url"] = _pdf_url(qid)
                resp["video_url"] = _video_url(qid)
                resp["quality"] = _quality(qid)
            resp["buildable"] = bool(qid) and all(_has_capture(g) for g in (ag.get("guides") or ([qid] if qid else [])))
            resp["sources"] = ag.get("sources", [])
            resp["section"] = ag.get("section") or section
            return resp
    except Exception as e:
        print("agent tier failed:", e)
    # Tier 0b: GPT brain understands the free-form question and routes to the right guide.
    try:
        from rag.smart_answer import answer as smart
        sm = smart(msg, history=history, section=section)
        if sm and sm.get("answer"):
            qid = sm.get("qid")
            if qid:
                # GPT did the routing; render the COMPLETE grounded steps (not a prose
                # summary) so the answer always has every step.
                from intelligence import agent
                full = agent.render(int(qid), msg, polish=bool(polish))
                resp = {"answer": full["answer"], "action": "single",
                        "qid": qid, "title": full["title"], "params": full["params"],
                        "guides": [qid], "pdf_url": _pdf_url(qid),
                        "video_url": _video_url(qid), "quality": _quality(qid),
                        "buildable": _has_capture(qid), "sources": full["sources"]}
            else:
                resp = {"answer": sm["answer"]}
            return resp
    except Exception as e:
        print("smart tier failed:", e)
    if _rag_ready():
        try:
            from rag.rag_engine import ask, retrieve, collection_stats
            if collection_stats().get("total_chunks", 0) > 0:
                try: answer = ask(msg)
                except Exception:
                    hits = retrieve(msg, n_results=3)
                    answer = "Here are the most relevant steps:\n\n" + "\n\n".join("- " + h["text"] for h in hits)
                hits = retrieve(msg, n_results=3)
                sources = [{"workflow": h["metadata"].get("workflow", ""),
                            "steps": f"{h['metadata'].get('step_start','')}-{h['metadata'].get('step_end','')}",
                            "similarity": h["similarity"]} for h in hits]
                return {"answer": answer, "sources": sources}
        except Exception as e:
            print("RAG tier failed:", e)
    from rag.simple_index import answer as simple_answer
    resp = simple_answer(msg)
    # No canonical guide matched -> offer the TYPED LANE: the live agent can attempt it
    # on the sandbox (POST /api/build_live with {"request": msg}).
    if isinstance(resp, dict):
        resp.setdefault("live_buildable", True)
        resp.setdefault("task", msg)
    return resp

@app.route("/api/chat", methods=["POST"])
def api_chat():
    body = request.get_json(force=True)
    return jsonify(handle_chat(body.get("message"), polish=bool(body.get("polish", True)),
                                   chat_memory=CHAT_MEMORY))

# ---- intelligence layer (self-healing / verify / feedback / health) ----
@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    b = request.get_json(force=True)
    try:
        from intelligence import feedback
        return jsonify(feedback.record(
            int(b.get("qid")), b.get("rating", "up"), step=b.get("step"),
            note=b.get("note", ""), selector=b.get("selector"),
            target=b.get("target"), url=b.get("url", "")))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/intelligence/health")
def api_intel_health():
    try:
        from intelligence import orchestrator
        return jsonify(orchestrator.health())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/verify/<int:qid>", methods=["POST"])
def api_verify(qid):
    try:
        from intelligence import verify
        return jsonify(verify.question(qid))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/restart", methods=["POST"])
def api_admin_restart():
    """LOCAL-ONLY maintenance: stop this server process (the background keep-alive too)
    so the Desktop icon can relaunch it with freshly edited code."""
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return jsonify({"error": "local only"}), 403
    def _die():
        import time as _t, os as _os
        _t.sleep(0.6)
        _os._exit(0)
    threading.Thread(target=_die, daemon=True).start()
    return jsonify({"ok": True, "message": "Server stopping - double-click the DISH "
                                           "Assistant icon to start it fresh."})

@app.route("/api/memory/status")
def api_memory_status():
    """RIM at a glance: diary size, outcomes, lessons, heals, chat facts."""
    try:
        from intelligence import memory, distill, resolver
        return jsonify({"experience": memory.stats(), "lessons": distill.stats(),
                        "resolver": resolver.stats()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/distill", methods=["POST"])
def api_distill():
    """Compress the experience diary into output/lessons.md (rules every agent reads)."""
    try:
        from intelligence import distill
        text = distill.run()
        return jsonify({"ok": True, "lessons": text, **distill.stats()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

BUILD = {"running": False, "qid": None, "log": [], "done": False, "output": None}


def _capture_headless():
    """Streamlit Cloud has no display — Playwright must run headless."""
    return bool(os.environ.get("STREAMLIT_SERVER_PORT"))


def _build_extra_vars(qid, request_text):
    """Parse product vars from a free-text ask (same rules as /api/build)."""
    if not request_text:
        return None, None
    try:
        from intelligence import agent
        params = agent.extract_params(request_text)
        extra_vars = agent.recipe_vars(int(qid), params) or None
        if params.get("is_add") and not (extra_vars or {}).get("NAME"):
            return None, ("I couldn't tell which product you mean. Tell me its exact name "
                          "(e.g. \"add a Cappuccino for 5 euro\") and I'll build the guide for it.")
        return extra_vars, None
    except Exception as e:
        print("build params parse failed:", e)
        return None, None


def run_build_sync(qid, do_capture=True, extra_vars=None, guides=None, headless=None, build_runner=None):
    """Blocking build for Streamlit (same pipeline as /api/build). Returns BUILD output dict."""
    if BUILD["running"]:
        return BUILD.get("output") or {}
    if build_runner:
        return build_runner(int(qid), bool(do_capture), extra_vars, guides) or {}
    _run_build(int(qid), bool(do_capture), extra_vars, guides, headless=headless)
    return BUILD.get("output") or {}


def auto_build_for_response(resp, request_text="", build_runner=None):
    """After /api/chat: auto-run capture + PDF/video when the widget would (widget.html send())."""
    qid = resp.get("qid")
    guides = resp.get("guides") or ([qid] if qid else [])
    buildable = resp.get("buildable")
    if qid and buildable is None:
        buildable = all(_has_capture(int(g)) for g in guides)
    if not qid or resp.get("action") in ("clarify", "none") or not buildable:
        return resp
    if _pdf_url(int(qid)) or _video_url(int(qid)):
        resp["pdf_url"] = resp.get("pdf_url") or _pdf_url(int(qid))
        resp["video_url"] = resp.get("video_url") or _video_url(int(qid))
        return resp
    g_list = None
    if isinstance(guides, list) and len(guides) > 1:
        g_list = [int(x) for x in guides]
    extra_vars, guard_msg = _build_extra_vars(qid, request_text)
    if guard_msg:
        resp["answer"] = resp.get("answer", "") + "\n\n⚠ " + guard_msg
        return resp
    out = run_build_sync(int(qid), do_capture=True, extra_vars=extra_vars, guides=g_list,
                         build_runner=build_runner)
    if out.get("not_found"):
        resp["answer"] = resp.get("answer", "") + "\n\n⚠ " + out.get("message", "")
    else:
        resp["pdf_url"] = out.get("pdf") or _pdf_url(int(qid))
        resp["video_url"] = out.get("video") or _video_url(int(qid))
    return resp


def prepare_guide_response(qid, polish=True, do_build=True, build_runner=None):
    """Pick-a-question flow (widget.html askAbout): build if needed, then render steps."""
    qid = int(qid)
    if do_build and _has_capture(qid) and not _pdf_url(qid):
        run_build_sync(qid, do_capture=True, build_runner=build_runner)
    from intelligence import agent
    full = agent.render(qid, "", polish=bool(polish))
    return {
        "answer": full["answer"],
        "qid": qid,
        "title": full.get("title", ""),
        "params": full.get("params", {}),
        "sources": full.get("sources", []),
        "buildable": _has_capture(qid),
        "quality": _quality(qid),
        "pdf_url": _pdf_url(qid),
        "video_url": _video_url(qid),
    }

def _adhoc_urls(qid, pdf_path):
    """URLs for a random-question PREVIEW build (separate from the canonical 25)."""
    pdf_url = ""
    try:
        p = Path(pdf_path)
        if p.exists():
            pdf_url = "/files/docs/%s?v=%d" % (p.name, int(p.stat().st_mtime))
    except Exception:
        pass
    video_url = ""
    vids = list(Path(VIDEO_DIR).glob("Q%02d_adhoc_*.mp4" % qid))
    if vids:
        latest = max(vids, key=lambda v: v.stat().st_mtime)
        video_url = "/files/videos/%s?v=%d" % (latest.name, int(latest.stat().st_mtime))
    return pdf_url, video_url

def _save_memory(qid, score):
    """When a build verifies well, remember HOW it was done — the product-agnostic
    navigation steps + the selectors that worked — so the setup can reuse/refer to it.
    The product itself is NEVER stored; recipes use {NAME}/{PRICE}/{MENUGROUP} placeholders
    filled from the current question."""
    if score is None or score < 90:
        return
    rec = json.loads((ROOT / "recipes" / ("Q%02d_capture.json" % qid)).read_text(encoding="utf-8"))
    actions = rec.get("actions", [])
    selectors = sorted({s for a in actions for key in ("highlight", "click", "drag", "to")
                        for s in (a.get(key, []) if isinstance(a.get(key), list) else [])})
    mem_path = ROOT / "output" / "memory.json"
    mem = {}
    if mem_path.exists():
        try: mem = json.loads(mem_path.read_text(encoding="utf-8"))
        except Exception: mem = {}
    mem[str(qid)] = {
        "qid": qid,
        "workflow_title": rec.get("workflow_title", ""),
        "verified_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "score": score,
        "note": "product-agnostic: product comes from the current question via {NAME}/{PRICE}/{MENUGROUP}",
        "steps": actions,            # how it navigated (order + every action)
        "selectors": selectors,      # the selectors that worked
    }
    mem_path.write_text(json.dumps(mem, indent=2), encoding="utf-8")
    print("MEMORY: saved verified recipe for Q%02d (score %s) -> output/memory.json" % (qid, score))
class _Tee:
    def write(self, s):
        for line in s.splitlines():
            if line.strip(): BUILD["log"].append(line.rstrip())
        try: sys.__stdout__.write(s)
        except Exception: pass
    def flush(self):
        try: sys.__stdout__.flush()
        except Exception: pass

def _backup_canonical(qid):
    """An adhoc preview reuses the canonical qid's manifest/screenshot/vframe paths.
    Snapshot them first so a random-question demo can never corrupt the canonical
    guide's data (the cause of 'my saved guides show the wrong product')."""
    import tempfile, shutil
    d = Path(tempfile.mkdtemp(prefix="canon_q%02d_" % qid))
    for name in ("manifest_q%02d.json" % qid, "manifest_q%02d_enriched.json" % qid):
        p = ROOT / "output" / name
        if p.exists():
            shutil.copy2(p, d / name)
    for sub in ("vframes", "screenshots"):
        src = ROOT / "output" / sub / ("q%02d" % qid)
        if src.exists():
            shutil.copytree(src, d / sub)
    return d


def _restore_canonical(qid, d):
    import shutil
    try:
        for name in ("manifest_q%02d.json" % qid, "manifest_q%02d_enriched.json" % qid):
            if (d / name).exists():
                shutil.copy2(d / name, ROOT / "output" / name)
        for sub in ("vframes", "screenshots"):
            bak = d / sub
            dst = ROOT / "output" / sub / ("q%02d" % qid)
            if bak.exists():
                shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(bak, dst)
        shutil.rmtree(d, ignore_errors=True)
        print("Canonical Q%02d data restored after the adhoc preview." % qid)
    except Exception as e:
        print("canonical restore warn:", e)


def _run_build(qid, do_capture, extra_vars=None, guides=None, headless=None):
    # A build is an ADHOC preview when it carries a custom product (random/free-text ask).
    # Adhoc previews must never overwrite the canonical Q01-25 files or questions.json.
    # When `guides` lists more than one guide (a merged answer), the capture runs them in
    # ONE continuous browser session and the PDF/video is a single combined walkthrough.
    guides = guides or [qid]
    composite = len(guides) > 1
    adhoc = bool(extra_vars)
    if headless is None:
        headless = _capture_headless()
    out = None
    snap = None
    if adhoc and not composite:
        try:
            snap = _backup_canonical(qid)
        except Exception as e:
            print("canonical backup warn:", e)
    try:
        BUILD.update(running=True, qid=qid, log=[], done=False, output=None)
        with contextlib.redirect_stdout(_Tee()):
            if adhoc:
                print("Random question -> building a PREVIEW (your saved guides stay untouched).")
            if composite:
                print("Multi-part question -> ONE continuous guide across %s."
                      % "+".join("Q%02d" % g for g in guides))
            nf = None
            if do_capture:
                try:
                    print("Logging into DISH POS and capturing every step (one session)...")
                    from capture import engine
                    res = engine.main(qid=qid, headless=headless, extra_vars=extra_vars, guides=guides)
                    if isinstance(res, dict) and res.get("name"):
                        nf = res["name"]
                except Exception as e:
                    print("Live capture unavailable (%s) - using existing screenshots." % e)
            if nf:
                # The named product isn't in the catalogue - reply smartly, don't build a
                # guide for the wrong product.
                BUILD["output"] = {"not_found": nf, "message":
                    "I couldn't find “%s” in your products. Add it first, then I can "
                    "change its price." % nf}
                print("Product not in catalogue - replying instead of building.")
                return
            print("Building PDF + video...")
            from generate import doc_generator
            out = (doc_generator.build_combined(guides, vars=extra_vars, adhoc=adhoc) if composite
                   else doc_generator.build(qid, vars=extra_vars, adhoc=adhoc))
            score = None; gate_result = None; vr = None
            try:    # self-check: score the build, then run the CONFIDENCE GATE
                from intelligence import verify
                vr = verify.combined(guides) if composite else verify.question(qid)
                score = (vr or {}).get("score")
                gate_result = verify.gate(vr)
            except Exception as e:
                print("verify/gate skipped (%s)" % str(e)[:80])
            try:    # RIM: write this attempt (success OR failure) into the experience diary
                from intelligence import memory as _mem
                title = next((q["title"] for q in load_questions() if q["id"] == qid), "Q%02d" % qid)
                task_desc = title + ((" [adhoc: %s]" % ", ".join("%s=%s" % kv for kv in extra_vars.items()))
                                     if extra_vars else "")
                _mem.record_build(qid, task_desc, None, vr, gate_result,
                                  kind="adhoc" if adhoc else "build")
            except Exception as e:
                print("experience memory skipped (%s)" % str(e)[:80])
            # Only the canonical 25 are indexed into the chat knowledge base; random
            # previews are never persisted into it.
            if not adhoc and not composite and _rag_ready():
                print("Indexing for chat...")
                from rag.rag_engine import ingest_manifest
                enr = "%s/manifest_q%02d_enriched.json" % (BASE_OUT, qid)
                ingest_manifest(enr, workflow_title="Q%02d" % qid)
            try:    # remember HOW it was done (product-agnostic) when verified good
                _save_memory(qid, score)
            except Exception as e:
                print("memory skipped (%s)" % str(e)[:80])
            print("All done.")
        if adhoc:
            pdf_url, video_url = _adhoc_urls(qid, out)
            BUILD["output"] = {"pdf": pdf_url, "video": video_url, "adhoc": True, "gate": gate_result}
        else:
            qs = load_questions()
            for q in qs:
                if q["id"] == qid:
                    q["status"] = "ready"; q["pdf"] = _pdf_url(qid); q["video"] = _video_url(qid)
            save_questions(qs)
            BUILD["output"] = {"pdf": _pdf_url(qid), "video": _video_url(qid), "gate": gate_result}
    except Exception as e:
        BUILD["log"].append("Build failed: %s" % e)
    finally:
        if snap:
            _restore_canonical(qid, snap)
        BUILD.update(running=False, done=True)

@app.route("/api/build/<int:qid>", methods=["POST"])
def api_build(qid):
    if BUILD["running"]: return jsonify({"error": "a build is already running"}), 409
    b = request.get_json(silent=True) or {}
    do_capture = bool(b.get("capture", False))
    # Optional: tailor the demo to a specific product. Accept either an explicit
    # {"product": {"name":..., "price":...}} or a free-text {"request": "add apple
    # juice cocktail as a drink"} that the agent parses into recipe vars.
    extra_vars = None
    try:
        prod = b.get("product") or {}
        if prod.get("name") or prod.get("price"):
            extra_vars = {}
            if prod.get("name"):  extra_vars["NAME"] = str(prod["name"])
            if prod.get("price"): extra_vars["PRICE"] = str(prod["price"])
        elif b.get("request"):
            from intelligence import agent
            params = agent.extract_params(b["request"])
            extra_vars = agent.recipe_vars(qid, params) or None
    except Exception as e:
        print("build params parse failed:", e)
    # UNDERSTANDING GUARD: when the request clearly ADDS a product but no concrete
    # product name could be understood, DO NOT build - the demo would silently create
    # the default sample ("Sparkling Water") and the PDF/video would not match what the
    # user asked. Ask for the product instead.
    if b.get("request"):
        try:
            from intelligence import agent
            prm = agent.extract_params(b["request"])
            if prm.get("is_add") and not (extra_vars or {}).get("NAME"):
                return jsonify({"started": False, "needs_product": True,
                                "message": "I couldn't tell which product you mean. Tell me "
                                           "its exact name (e.g. \"add a Cappuccino for 5 "
                                           "euro\") and I'll build the guide for it."})
        except Exception as e:
            print("build guard failed:", e)
    # For a merged answer the chat sends the full guide list so the build can stitch every
    # part into ONE continuous walkthrough. Sanitize to ints; default to just this qid.
    guides = None
    try:
        g = b.get("guides")
        if isinstance(g, list) and len(g) > 1:
            guides = [int(x) for x in g]
    except Exception:
        guides = None
    threading.Thread(target=_run_build, args=(qid, do_capture, extra_vars, guides), daemon=True).start()
    return jsonify({"started": True, "qid": qid, "capture": do_capture, "vars": extra_vars, "guides": guides})

# ──────────────────────────────────────────────────────────────────────────────
#  TYPED LANE — live-agent build for BRAND-NEW questions (no recipe exists yet).
#  Flow: live_agent drives the sandbox -> caption→script bridge -> build PDF/video
#  -> verify (self-check) -> gate -> if it PASSES, promote into the recipe library.
# ──────────────────────────────────────────────────────────────────────────────
LIVE_TMP_QID = 90   # scratch id for the live preview; a promoted run gets a real id

def _relabel_artifacts(src, dst):
    """Copy a temp live build's artifacts to the promoted qid so the new dropdown
    entry shows its PDF / video / score immediately."""
    import shutil
    for p in Path(DOCS_DIR).glob("Q%02d_branded_*.pdf" % src):
        shutil.copy2(p, Path(DOCS_DIR) / p.name.replace("Q%02d" % src, "Q%02d" % dst, 1))
    for p in Path(VIDEO_DIR).glob("Q%02d_walkthrough*.mp4" % src):
        shutil.copy2(p, Path(VIDEO_DIR) / p.name.replace("Q%02d" % src, "Q%02d" % dst, 1))
    for nm in ("manifest_q%02d.json", "manifest_q%02d_enriched.json", "verify_q%02d.json"):
        sp = ROOT / "output" / (nm % src)
        if sp.exists():
            shutil.copy2(sp, ROOT / "output" / (nm % dst))
    sf = ROOT / "output" / "vframes" / ("q%02d" % src)
    df = ROOT / "output" / "vframes" / ("q%02d" % dst)
    if sf.exists():
        if df.exists():
            shutil.rmtree(df, ignore_errors=True)
        shutil.copytree(sf, df)

def _cleanup_temp(qid):
    import shutil
    for p in list(Path(DOCS_DIR).glob("Q%02d_branded_*.pdf" % qid)) + \
             list(Path(VIDEO_DIR).glob("Q%02d_walkthrough*.mp4" % qid)):
        try: p.unlink()
        except Exception: pass
    for nm in ("manifest_q%02d.json", "manifest_q%02d_live.json",
               "manifest_q%02d_enriched.json", "verify_q%02d.json"):
        try: (ROOT / "output" / (nm % qid)).unlink()
        except Exception: pass
    try: (ROOT / "recipes" / ("Q%02d_script.json" % qid)).unlink()
    except Exception: pass
    for d in (ROOT / "output" / "vframes" / ("q%02d" % qid),
              ROOT / "output" / "screenshots" / ("q%02d_live" % qid)):
        shutil.rmtree(d, ignore_errors=True)

def _run_live_build(task, section=None):
    promoted = None; gate_result = None
    try:
        BUILD.update(running=True, qid=LIVE_TMP_QID, log=[], done=False, output=None)
        with contextlib.redirect_stdout(_Tee()):
            print("Brand-new question -> the live agent will attempt it on the SANDBOX.")
            from intelligence import live_agent
            man = live_agent.solve(task, qid=LIVE_TMP_QID, headless=False)
            if not man or man.get("error"):
                BUILD["output"] = {"error": (man or {}).get("error", "live agent failed"), "live": True}
                return
            caps = man.get("captions", [])
            shots = sorted(man.get("screenshots", []), key=lambda s: s.get("step", 0))
            if not shots:
                BUILD["output"] = {"error": "live agent captured no steps", "live": True}
                return
            # caption -> script bridge (the builder reads captions from a script file)
            steps = [{"step": s["step"],
                      "caption": (caps[i] if i < len(caps) else "Step %d" % s["step"]),
                      "action": "click"} for i, s in enumerate(shots)]
            (ROOT / "recipes" / ("Q%02d_script.json" % LIVE_TMP_QID)).write_text(
                json.dumps({"id": LIVE_TMP_QID, "title": task, "workflow_title": task,
                            "steps": steps}, indent=2), encoding="utf-8")
            (ROOT / "output" / ("manifest_q%02d.json" % LIVE_TMP_QID)).write_text(
                json.dumps(man, indent=2), encoding="utf-8")
            print("Building PDF + video from the live run...")
            from generate import doc_generator
            out = doc_generator.build(LIVE_TMP_QID, adhoc=False)
            if not out:
                BUILD["output"] = {"error": "build produced no pages (no screenshots resolved)", "live": True}
                return
            from intelligence import verify
            vr = verify.question(LIVE_TMP_QID)
            gate_result = verify.gate(vr)
            if gate_result.get("decision") == "publish":
                from intelligence import promote
                promoted = promote.promote(task, section, man.get("actions", []), caps, gate_result)
                if promoted:
                    _relabel_artifacts(LIVE_TMP_QID, promoted)
            try:    # RIM: live attempts (pass OR fail) are the richest experiences of all
                from intelligence import memory as _mem
                _mem.record_build(promoted or LIVE_TMP_QID, task, section, vr, gate_result,
                                  kind="live", details={"promoted": bool(promoted)})
            except Exception as e:
                print("experience memory skipped (%s)" % str(e)[:80])
            print("Live build complete. gate=%s  promoted=%s" %
                  (gate_result.get("decision"), promoted))
        if promoted:
            BUILD["output"] = {"pdf": _pdf_url(promoted), "video": _video_url(promoted),
                               "gate": gate_result, "promoted_qid": promoted,
                               "title": task, "live": True}
            _cleanup_temp(LIVE_TMP_QID)
        else:
            BUILD["output"] = {"pdf": _pdf_url(LIVE_TMP_QID), "video": _video_url(LIVE_TMP_QID),
                               "gate": gate_result, "promoted_qid": None,
                               "needs_review": True, "title": task, "live": True}
    except Exception as e:
        BUILD["log"].append("Live build failed: %s" % e)
        BUILD["output"] = {"error": str(e), "live": True}
    finally:
        BUILD.update(running=False, done=True)

@app.route("/api/build_live", methods=["POST"])
def api_build_live():
    """TYPED LANE: drive a brand-new question live on the sandbox, self-check it,
    gate it, and (only if it passes) promote it into the recipe library/dropdown."""
    if BUILD["running"]:
        return jsonify({"error": "a build is already running"}), 409
    b = request.get_json(silent=True) or {}
    task = (b.get("request") or b.get("task") or b.get("message") or "").strip()
    if not task:
        return jsonify({"error": "no task text provided"}), 400
    section = None
    try:
        from intelligence import agent
        section = agent.dominant_section(task)
    except Exception:
        section = None
    threading.Thread(target=_run_live_build, args=(task, section), daemon=True).start()
    return jsonify({"started": True, "live": True, "task": task})

@app.route("/api/build/status")
def api_build_status():
    return jsonify(BUILD)

@app.route("/files/<kind>/<path:fname>")
def files(kind, fname):
    folder = {"docs": DOCS_DIR, "videos": VIDEO_DIR}.get(kind)
    if not folder: abort(404)
    return send_from_directory(folder, fname)

def _lan_ip():
    """Best-effort LAN IP of this machine so colleagues on the same Wi-Fi can connect."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80)); return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

if __name__ == "__main__":
    ip = _lan_ip()
    print("=" * 60)
    print(" DISH Docs chatbot is running")
    print("   Local  (this PC):        http://127.0.0.1:5000")
    print("   Network (same Wi-Fi):    http://%s:5000" % ip)
    print("   ^ share the Network link with colleagues on the same Wi-Fi.")
    print("=" * 60)
    # host=0.0.0.0 exposes it on the local network (not the public internet).
    app.run(host="0.0.0.0", port=5000, threaded=True, use_reloader=False)
