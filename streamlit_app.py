# streamlit_app.py — DISH chatbot UI (same brain + automation as server.py / widget.html).
import os
import sys
import threading
import time
from collections import deque
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

for _key in ("OPENAI_API_KEY", "DISH_EMAIL", "DISH_PASSWORD", "LLM_MODEL"):
    try:
        if _key in st.secrets:
            os.environ[_key] = str(st.secrets[_key])
    except Exception:
        pass

from config.settings import DOCS_DIR, VIDEO_DIR
from server import (
    handle_chat, load_questions, _has_capture, _quality, _pdf_url, _video_url,
    auto_build_for_response, prepare_guide_response, _run_build, BUILD,
)
import streamlit_remote as remote

APP_VERSION = "v3.3"
RENDER_DEPLOY = "https://dashboard.render.com/select-repo?type=web"
GITHUB_REPO = "yashwantreddyvarra-bot/dish-ai-knowledge-operations"

st.set_page_config(
    page_title="DISH POS Assistant",
    page_icon="🍽️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

ORANGE = "#EC6A38"
SECTIONS = ["", "Products", "Self-service", "Payment"]
SECTION_LABELS = {"": "All", "Products": "Products", "Self-service": "Self-service", "Payment": "Payment"}


def _backend_url():
    try:
        u = str(st.secrets.get("BACKEND_URL", "") or "").strip()
        if u:
            return u.rstrip("/")
    except Exception:
        pass
    return os.getenv("BACKEND_URL", "").strip().rstrip("/")


def _inject_css():
    st.markdown(
        """
        <style>
        #MainMenu, footer, header { visibility: hidden; }
        .block-container { padding-top: 0.8rem; max-width: 420px; }
        .dish-hd {
            background: %s; color: #fff; padding: 12px 14px; border-radius: 14px 14px 0 0;
            display: flex; align-items: center; gap: 10px; margin: 0 -1rem;
        }
        .dish-hd .logo {
            width: 30px; height: 30px; border-radius: 8px; background: rgba(255,255,255,.22);
            display: flex; align-items: center; justify-content: center; font-weight: 700;
        }
        .dish-hd .ttl b { font-size: 14px; }
        .dish-hd .ttl small { display: block; font-size: 11px; opacity: .92; font-weight: 400; }
        .dish-panel {
            border: 1px solid #e7e8ec; border-radius: 14px; overflow: hidden;
            box-shadow: 0 10px 40px rgba(0,0,0,.08); background: #fff; margin: 0 -1rem;
        }
        .dish-pick { padding: 10px 12px 4px; border-bottom: 1px solid #e7e8ec; }
        .dish-empty {
            text-align: center; color: #6b7280; font-size: 13px; padding: 28px 12px; line-height: 1.6;
        }
        .dish-empty .big { font-size: 34px; }
        div[data-testid="stChatMessage"] {
            background: transparent !important; border: none !important; padding: 4px 0 !important;
        }
        div[data-testid="stChatMessageAvatarUser"] {
            background: %s !important;
        }
        div[data-testid="stChatMessageAvatarAssistant"] {
            background: #f5f6f8 !important; color: %s !important; border: 1px solid #e7e8ec;
        }
        .stChatMessage .stMarkdown {
            background: #f5f6f8; border: 1px solid #e7e8ec; border-radius: 13px;
            border-bottom-left-radius: 4px; padding: 10px 13px; font-size: 13px; line-height: 1.55;
        }
        div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) .stMarkdown {
            background: %s !important; color: #fff !important; border: none !important;
            border-bottom-right-radius: 4px !important; border-bottom-left-radius: 13px !important;
        }
        .quality-badge {
            margin-top: 10px; font-size: 11.5px; display: inline-flex; align-items: center; gap: 6px;
            border: 1px solid; border-radius: 8px; padding: 5px 9px; background: #fff;
        }
        .src-line { margin-top: 8px; font-size: 10.5px; color: #6b7280;
            border-top: 1px dashed #e7e8ec; padding-top: 6px; }
        .attach-row { margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap; }
        .attach-row a {
            font-size: 12px; font-weight: 600; text-decoration: none; padding: 7px 11px;
            border-radius: 8px; background: %s; color: #fff; display: inline-block;
        }
        .attach-row a.sec { background: #fff; color: %s; border: 1px solid %s; }
        .activity-box {
            background: #1d2027; color: #cfe8cf; border-radius: 13px; padding: 10px 12px;
            font-size: 12px; font-family: ui-monospace, Consolas, monospace; margin: 8px 0;
            max-height: 160px; overflow: auto; white-space: pre-wrap; line-height: 1.55;
        }
        </style>
        """
        % (ORANGE, ORANGE, ORANGE, ORANGE, ORANGE, ORANGE, ORANGE),
        unsafe_allow_html=True,
    )


def _init_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_memory" not in st.session_state:
        st.session_state.chat_memory = deque(maxlen=6)
    if "section_filter" not in st.session_state:
        st.session_state.section_filter = ""
    if "polish" not in st.session_state:
        st.session_state.polish = True


def _latest_file(folder, pattern):
    hits = list(Path(folder).glob(pattern))
    return max(hits, key=lambda p: p.stat().st_mtime) if hits else None


def _quality_badge(quality):
    if not quality or quality.get("score") is None:
        return
    score = quality["score"]
    color = "#1a7f37" if score >= 85 else "#b7791f" if score >= 70 else "#c23b3b"
    issues = (
        "%d step issue%s" % (quality["fail"], "s" if quality.get("fail", 0) != 1 else "")
        if quality.get("fail")
        else "verified clean"
    )
    extra = ""
    if quality.get("pdf_score") is not None:
        extra = (
            " (PDF %s · Video %s · Steps %s)"
            % (quality.get("pdf_score"), quality.get("video_score"), quality.get("steps_score"))
        )
    st.markdown(
        '<div class="quality-badge" style="border-color:%s;color:%s">'
        '<span style="width:8px;height:8px;border-radius:50%%;background:%s;display:inline-block"></span>'
        "Quality <b>%s/100</b> · %s%s</div>"
        % (color, color, color, score, issues, extra),
        unsafe_allow_html=True,
    )


def _fname_from_media_url(url):
    if not url:
        return ""
    return url.split("/")[-1].split("?")[0]


def _resolve_media(qid=None, pdf_url=None, video_url=None):
    """Same file lookup as server.py _pdf_url / _video_url, resolved to disk paths."""
    if qid:
        pdf_url = pdf_url or _pdf_url(int(qid))
        video_url = video_url or _video_url(int(qid))
    pdf_path = vid_path = None
    if pdf_url:
        p = Path(DOCS_DIR) / _fname_from_media_url(pdf_url)
        if p.exists():
            pdf_path = p
    if video_url:
        v = Path(VIDEO_DIR) / _fname_from_media_url(video_url)
        if v.exists():
            vid_path = v
    if qid and not pdf_path:
        pdf_path = _latest_file(DOCS_DIR, "Q%02d_branded_*.pdf" % int(qid))
    if qid and not vid_path:
        vid_path = _latest_file(VIDEO_DIR, "Q%02d_walkthrough*.mp4" % int(qid))
    return pdf_url, video_url, pdf_path, vid_path


def _show_media(pdf_url, video_url, pdf_path, vid_path, note="", backend_base=""):
    """Mirror widget.html appendMedia: PDF link + inline video player."""
    if backend_base:
        if pdf_url:
            full = remote.abs_media_url(backend_base, pdf_url)
            st.markdown(
                '<div class="attach-row"><a href="%s" target="_blank">📄 Open PDF</a></div>'
                % __import__("html").escape(full), unsafe_allow_html=True)
        if video_url:
            st.video(remote.abs_media_url(backend_base, video_url))
            if note:
                st.markdown('<div class="vnote">%s</div>' % note, unsafe_allow_html=True)
        return
    if not pdf_path and not vid_path:
        return
    links = []
    if pdf_path and pdf_path.exists():
        links.append(
            '<a href="data:application/pdf;base64,%s" target="_blank" download="%s">📄 Open PDF</a>'
            % (__import__("base64").b64encode(pdf_path.read_bytes()).decode(), pdf_path.name)
        )
    if vid_path and vid_path.exists():
        links.append('<span class="sec" style="padding:7px 11px;border-radius:8px;border:1px solid %s;color:%s;font-size:12px;font-weight:600">🎬 Video below</span>' % (ORANGE, ORANGE))
    if links:
        st.markdown('<div class="attach-row">%s</div>' % "".join(links), unsafe_allow_html=True)
    if vid_path and vid_path.exists():
        st.video(str(vid_path))
        if note:
            st.markdown('<div class="vnote">%s</div>' % note, unsafe_allow_html=True)


def _show_bot_extras(resp):
    qid = resp.get("qid")
    base = _backend_url()
    if resp.get("build_error"):
        st.error(resp["build_error"])
    if resp.get("build_log"):
        with st.expander("Build log", expanded=False):
            st.code("\n".join(resp["build_log"][-20:]))
    if resp.get("title"):
        st.caption(resp["title"])
    _quality_badge(resp.get("quality") or (_quality(int(qid)) if qid else None))
    pdf_url, video_url, pdf_path, vid_path = _resolve_media(
        qid=qid, pdf_url=resp.get("pdf_url"), video_url=resp.get("video_url"))
    _show_media(pdf_url, video_url, pdf_path, vid_path, backend_base=base)
    if qid and not pdf_url and not vid_path and not pdf_path and not vid_path:
        if base:
            st.warning("Backend did not return PDF/video yet. Check that server.py is running.")
        elif resp.get("buildable"):
            st.warning(
                "Live capture cannot run on Streamlit Cloud alone. "
                "Add BACKEND_URL in Secrets (your desktop server.py + tunnel) "
                "or run: streamlit run streamlit_app.py on your Mac/PC."
            )
    sources = resp.get("sources") or []
    if sources:
        parts = []
        for s in sources:
            if isinstance(s, dict):
                line = s.get("workflow", "step")
                if s.get("steps"):
                    line += " (steps %s)" % s["steps"]
                parts.append(line)
        if parts:
            st.markdown(
                '<div class="src-line">Sources: %s</div>' % "  ·  ".join(parts),
                unsafe_allow_html=True,
            )
    if resp.get("live_buildable"):
        st.caption("Brand-new tasks without a saved recipe need the desktop live-agent lane.")


def _log_runner(log_lines):
    st.session_state._last_build_log = list(log_lines)


def _build_runner(qid, do_capture, extra_vars, guides):
    """Live build log panel — mirrors widget.html activity box."""
    if BUILD["running"]:
        return BUILD.get("output") or {}
    label = "Building your guide live…"
    with st.status(label, expanded=True) as box:
        log_ph = st.empty()

        def _work():
            _run_build(qid, do_capture, extra_vars, guides)

        t = threading.Thread(target=_work, daemon=True)
        t.start()
        while t.is_alive():
            lines = BUILD.get("log", [])
            log_ph.markdown(
                '<div class="activity-box">%s</div>'
                % (__import__("html").escape("\n".join(lines[-16:]) if lines else "Starting…")),
                unsafe_allow_html=True,
            )
            time.sleep(0.35)
        t.join()
        lines = BUILD.get("log", [])
        log_ph.markdown(
            '<div class="activity-box">%s</div>'
            % (__import__("html").escape("\n".join(lines[-16:]) if lines else "Done.")),
            unsafe_allow_html=True,
        )
        out = BUILD.get("output") or {}
        if not out.get("pdf") and not out.get("video"):
            err = "\n".join(BUILD.get("log", [])[-8:])
            if err:
                st.warning("Build finished but no PDF/video. Log:\n" + err)
        box.update(label="✓ Guide ready" if out and not out.get("not_found") else "Build finished",
                   state="complete")
    return BUILD.get("output") or {}


def _ask(msg, polish=True):
    base = _backend_url()
    if base:
        with st.status("Connecting to backend…", expanded=True) as box:
            log_ph = st.empty()

            def on_log(lines):
                log_ph.markdown(
                    '<div class="activity-box">%s</div>'
                    % __import__("html").escape("\n".join(lines[-16:])),
                    unsafe_allow_html=True,
                )

            try:
                resp = remote.chat_with_build(base, msg, polish=polish, on_log=on_log)
                box.update(label="✓ Backend ready", state="complete")
                return resp
            except Exception as e:
                box.update(label="Backend error", state="error")
                return {"answer": "Cannot reach backend at %s\n\n%s" % (base, e)}
    with st.spinner("Thinking…"):
        resp = handle_chat(msg, polish=polish, chat_memory=st.session_state.chat_memory)
    return auto_build_for_response(resp, msg, build_runner=_build_runner)


def _render_guide(qid, title, polish=True):
    q = "How do I %s%s?" % (title[0].lower(), title[1:]) if title else "Show me this guide"
    base = _backend_url()
    if base:
        with st.status("Loading guide from backend…", expanded=True) as box:
            log_ph = st.empty()

            def on_log(lines):
                log_ph.markdown(
                    '<div class="activity-box">%s</div>'
                    % __import__("html").escape("\n".join(lines[-16:])),
                    unsafe_allow_html=True,
                )

            try:
                resp = remote.guide_with_build(base, qid, polish=polish, on_log=on_log)
                box.update(label="✓ Guide ready", state="complete")
                return q, resp
            except Exception as e:
                box.update(label="Backend error", state="error")
                return q, {"answer": "Backend error: %s" % e}
    resp = prepare_guide_response(qid, polish=polish, build_runner=_build_runner)
    return q, resp


def _filtered_questions():
    qs = load_questions()
    f = st.session_state.section_filter
    return [q for q in qs if not f or q.get("section") == f]


def _on_section_pick(section):
    st.session_state.section_filter = section
    st.session_state.question_pick = 0


def _on_question_pick():
    idx = st.session_state.question_pick
    if not idx:
        return
    qs = _filtered_questions()
    if idx < 1 or idx > len(qs):
        return
    q = qs[idx - 1]
    user_msg, resp = _render_guide(q["id"], q["title"], polish=st.session_state.polish)
    st.session_state.messages.append({"role": "user", "content": user_msg})
    st.session_state.messages.append({"role": "assistant", "content": resp})
    st.session_state.question_pick = 0


def _render_header():
    st.markdown(
        """
        <div class="dish-panel">
          <div class="dish-hd">
            <div class="logo">D</div>
            <div class="ttl"><b>DISH POS Assistant</b><small>Products · Self-service · Payment</small></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _show_setup_help():
    st.error("**To get PDF + video + live builds for everyone worldwide, connect a 24/7 backend (5 min setup).**")
    st.markdown("""
### Option 1 — Cloud backend (recommended: no PC needed)

1. **Deploy backend** → [Open Render.com](%s)  
   - Connect GitHub → repo **`%s`** → branch **`feature/dish-doc-automation`**  
   - Runtime: **Docker**  
   - Add env vars: `OPENAI_API_KEY`, `DISH_EMAIL`, `DISH_PASSWORD`  
   - Wait for deploy → copy URL like `https://dish-backend-xxxx.onrender.com`

2. **Test backend** — open `https://YOUR-RENDER-URL/widget` (orange chatbot should appear)

3. **Streamlit Secrets** (Settings → Secrets):
```toml
OPENAI_API_KEY = "sk-your-key"
BACKEND_URL = "https://YOUR-RENDER-URL.onrender.com"
DISH_EMAIL = "your-dish-login"
DISH_PASSWORD = "your-dish-password"
```

4. **Save → Reboot app** → share your `.streamlit.app` link with anyone

---

### Option 2 — Your Windows PC (if Render fails)

1. Run **`setup_windows.bat`** then **`start_backend.bat`**
2. Copy the `https://....trycloudflare.com` URL into `BACKEND_URL` in Secrets
3. Keep your PC on while people use the app

See **`START_HERE.txt`** in the GitHub repo for full instructions.
""" % (RENDER_DEPLOY, GITHUB_REPO))


def main():
    _init_state()
    _inject_css()
    base = _backend_url()

    # When backend is connected → embed the exact Flask widget (PDF, video, live build).
    if base:
        _render_header()
        st.caption("**%s** · Full server.py widget via %s" % (APP_VERSION, base))
        try:
            import urllib.request
            urllib.request.urlopen(base + "/widget", timeout=8)
            st.components.v1.iframe(base + "/widget", height=720, scrolling=True)
        except Exception as e:
            st.warning("Backend not reachable: %s" % e)
            st.caption("Make sure `start_backend.bat` is running on your PC and BACKEND_URL is correct.")
        with st.expander("Settings"):
            st.session_state.polish = st.checkbox("Polish answers (LLM)", value=st.session_state.polish)
        return

    _render_header()
    st.caption("**%s** · No BACKEND_URL — text-only on cloud" % APP_VERSION)
    _show_setup_help()

    with st.container():
        st.markdown('<div class="dish-pick">', unsafe_allow_html=True)
        cols = st.columns(4)
        for i, sec in enumerate(SECTIONS):
            label = SECTION_LABELS[sec]
            active = st.session_state.section_filter == sec
            if cols[i].button(
                label,
                key="chip_%s" % (sec or "all"),
                type="primary" if active else "secondary",
                use_container_width=True,
            ):
                _on_section_pick(sec)
                st.rerun()

        qs = _filtered_questions()
        options = ["Choose a question…"] + [
            "Q%02d. %s%s" % (q["id"], q["title"], "  ✅" if q.get("pdf") else "") for q in qs
        ]
        st.selectbox(
            "Guide",
            range(len(options)),
            format_func=lambda i: options[i],
            key="question_pick",
            label_visibility="collapsed",
            on_change=_on_question_pick,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    if not st.session_state.messages:
        st.markdown(
            '<div class="dish-empty"><div class="big">💬</div>Pick a question above,<br/>or type your own below.</div>',
            unsafe_allow_html=True,
        )

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            content = msg["content"]
            if isinstance(content, dict):
                st.markdown(content.get("answer", ""))
                _show_bot_extras(content)
            else:
                st.markdown(content)

    with st.expander("Settings", expanded=False):
        st.session_state.polish = st.checkbox("Polish answers (LLM)", value=st.session_state.polish)
        if st.button("Clear chat"):
            st.session_state.messages = []
            st.session_state.chat_memory = deque(maxlen=6)
            st.rerun()
        key = os.getenv("OPENAI_API_KEY", "")
        st.caption("OpenAI key: %s" % ("set ✓" if key else "not set"))
        st.caption("BACKEND_URL: %s" % (base or "not set — add for live PDF/video"))
        st.caption("After code updates: Streamlit menu → **Reboot app**")

    prompt = st.chat_input("Ask anything…")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        try:
            resp = _ask(prompt, polish=st.session_state.polish)
        except Exception as e:
            resp = {"answer": "Sorry, something went wrong: %s" % e}
        st.session_state.messages.append({"role": "assistant", "content": resp})
        st.rerun()


if __name__ == "__main__":
    main()
