# streamlit_app.py — DISH chatbot UI (same brain as server.py, styled like widget.html).
import os
import sys
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
from server import handle_chat, load_questions, _has_capture, _quality

st.set_page_config(
    page_title="DISH POS Assistant",
    page_icon="🍽️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

ORANGE = "#EC6A38"
SECTIONS = ["", "Products", "Self-service", "Payment"]
SECTION_LABELS = {"": "All", "Products": "Products", "Self-service": "Self-service", "Payment": "Payment"}


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
        div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
            border-radius: 999px; font-size: 11px; padding: 4px 11px;
        }
        </style>
        """
        % (ORANGE, ORANGE, ORANGE, ORANGE),
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


def _show_bot_extras(resp):
    qid = resp.get("qid")
    if resp.get("title"):
        st.caption(resp["title"])
    _quality_badge(resp.get("quality") or (_quality(int(qid)) if qid else None))
    if qid:
        pdf = _latest_file(DOCS_DIR, "Q%02d_branded_*.pdf" % int(qid))
        if pdf and pdf.exists():
            st.download_button("📄 Open PDF", pdf.read_bytes(), file_name=pdf.name, mime="application/pdf")
        vid = _latest_file(VIDEO_DIR, "Q%02d_walkthrough*.mp4" % int(qid))
        if vid and vid.exists():
            st.video(str(vid))
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
        st.caption("Live PDF/video builds run on the desktop Flask app (Playwright).")


def _ask(msg, polish=True):
    with st.spinner("Thinking…"):
        return handle_chat(msg, polish=polish, chat_memory=st.session_state.chat_memory)


def _render_guide(qid, title, polish=True):
    from intelligence import agent
    full = agent.render(int(qid), "", polish=polish)
    q = "How do I %s%s?" % (title[0].lower(), title[1:]) if title else "Show me this guide"
    return q, {
        "answer": full["answer"],
        "qid": qid,
        "title": full.get("title", title),
        "sources": full.get("sources", []),
        "buildable": _has_capture(qid),
        "quality": _quality(qid),
    }


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


def main():
    _init_state()
    _inject_css()
    _render_header()

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
        st.caption("OpenAI key: %s" % ("set ✓" if key else "not set — add in Streamlit Secrets"))

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
