# streamlit_app.py — Streamlit front-end for the DISH chatbot (same brain as server.py).
# Run locally:  streamlit run streamlit_app.py
# Deploy: push to GitHub → share.streamlit.io → point at this file.
import os
import sys
from collections import deque
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Streamlit Cloud secrets → env vars (before importing server / config).
for _key in ("OPENAI_API_KEY", "DISH_EMAIL", "DISH_PASSWORD", "LLM_MODEL"):
    try:
        if _key in st.secrets:
            os.environ[_key] = str(st.secrets[_key])
    except Exception:
        pass

from config.settings import DOCS_DIR, VIDEO_DIR
from server import handle_chat, load_questions, _has_capture, _quality

st.set_page_config(page_title="DISH POS Assistant", page_icon="🍽️", layout="centered")

ORANGE = "#EC6A38"


def _init_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_memory" not in st.session_state:
        st.session_state.chat_memory = deque(maxlen=6)


def _latest_file(folder, pattern):
    hits = list(Path(folder).glob(pattern))
    return max(hits, key=lambda p: p.stat().st_mtime) if hits else None


def _show_attachments(resp):
    qid = resp.get("qid")
    if not qid:
        return
    pdf = _latest_file(DOCS_DIR, "Q%02d_branded_*.pdf" % int(qid))
    if pdf and pdf.exists():
        st.download_button("Download PDF guide", pdf.read_bytes(),
                           file_name=pdf.name, mime="application/pdf")
    vid = _latest_file(VIDEO_DIR, "Q%02d_walkthrough*.mp4" % int(qid))
    if vid and vid.exists():
        st.video(str(vid))
    quality = resp.get("quality") or _quality(int(qid))
    if quality and quality.get("score") is not None:
        st.caption("Guide quality score: %s/100" % quality["score"])


def _show_sources(resp):
    sources = resp.get("sources") or []
    if not sources:
        return
    with st.expander("Sources"):
        for s in sources:
            if isinstance(s, dict):
                wf = s.get("workflow", "")
                steps = s.get("steps", "")
                sim = s.get("similarity")
                line = wf or "step"
                if steps:
                    line += " (%s)" % steps
                if sim is not None:
                    line += " — match %.0f%%" % (float(sim) * 100)
                st.markdown("- %s" % line)
            else:
                st.markdown("- %s" % s)


def _ask(msg, polish=True):
    with st.spinner("Thinking…"):
        return handle_chat(msg, polish=polish, chat_memory=st.session_state.chat_memory)


def _render_guide(qid, polish=True):
    from intelligence import agent
    full = agent.render(int(qid), "", polish=polish)
    return {
        "answer": full["answer"],
        "qid": qid,
        "title": full["title"],
        "sources": full.get("sources", []),
        "buildable": _has_capture(qid),
        "quality": _quality(qid),
    }


def main():
    _init_state()

    st.markdown(
        "<h2 style='color:%s;margin-bottom:0'>DISH POS Assistant</h2>"
        "<p style='color:#6b7280;margin-top:4px'>Same chat engine as <code>server.py</code> — deployed on Streamlit.</p>"
        % ORANGE,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Guides")
        qs = load_questions()
        labels = ["— pick a guide —"] + ["Q%02d: %s" % (q["id"], q["title"]) for q in qs]
        pick = st.selectbox("Ask about this", labels, label_visibility="collapsed")
        if st.button("Show guide steps", use_container_width=True) and pick != labels[0]:
            qid = int(pick.split(":")[0].replace("Q", ""))
            resp = _render_guide(qid)
            st.session_state.messages.append({"role": "user", "content": "Show me: %s" % pick})
            st.session_state.messages.append({"role": "assistant", "content": resp})
            st.rerun()

        st.divider()
        polish = st.checkbox("Polish answers (LLM)", value=True)
        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.chat_memory = deque(maxlen=6)
            st.rerun()

        st.caption("Deploy on [Streamlit Cloud](https://share.streamlit.io) from GitHub.")
        key = os.getenv("OPENAI_API_KEY", "")
        st.caption("OpenAI key: %s" % ("set ✓" if key else "not set (add in Secrets)"))

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            content = msg["content"]
            if isinstance(content, dict):
                st.markdown(content.get("answer", ""))
                if content.get("title"):
                    st.caption(content["title"])
                _show_attachments(content)
                _show_sources(content)
                if content.get("live_buildable"):
                    st.info("Live PDF/video builds need the desktop Flask app (Playwright).")
            else:
                st.markdown(content)

    prompt = st.chat_input("Ask about Products, menus, forms…")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            try:
                resp = _ask(prompt, polish=polish)
            except Exception as e:
                resp = {"answer": "Sorry, something went wrong: %s" % e}
            st.markdown(resp.get("answer", ""))
            if resp.get("title"):
                st.caption(resp["title"])
            _show_attachments(resp)
            _show_sources(resp)
            if resp.get("live_buildable"):
                st.info("Live PDF/video builds need the desktop Flask app (Playwright).")
        st.session_state.messages.append({"role": "assistant", "content": resp})


if __name__ == "__main__":
    main()
