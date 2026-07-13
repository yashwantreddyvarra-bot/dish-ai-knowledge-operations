# streamlit_remote.py — call a running server.py instance (desktop + tunnel) from Streamlit Cloud.
import json
import time
import urllib.error
import urllib.request

TIMEOUT = 180


def _url(base, path):
    return base.rstrip("/") + path


def _get(base, path):
    req = urllib.request.Request(_url(base, path), method="GET")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def _post(base, path, body):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        _url(base, path), data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def chat(base, message, polish=True):
    return _post(base, "/api/chat", {"message": message, "polish": bool(polish)})


def question_detail(base, qid):
    return _get(base, "/api/question/%d" % int(qid))


def render_guide(base, qid, polish=True):
    return _get(base, "/api/render/%d?polish=%d" % (int(qid), 1 if polish else 0))


def start_build(base, qid, request_text="", guides=None):
    body = {"capture": True}
    if request_text:
        body["request"] = request_text
    if guides and len(guides) > 1:
        body["guides"] = [int(g) for g in guides]
    return _post(base, "/api/build/%d" % int(qid), body)


def build_status(base):
    return _get(base, "/api/build/status")


def poll_build(base, on_log=None, max_wait=600):
    """Wait for /api/build/status done=True. Yields status dicts."""
    deadline = time.time() + max_wait
    last = []
    while time.time() < deadline:
        st = build_status(base)
        log = st.get("log") or []
        if on_log and log != last:
            on_log(log)
            last = list(log)
        yield st
        if st.get("done"):
            return st
        time.sleep(1.0)
    return st


def abs_media_url(base, url):
    if not url:
        return ""
    if url.startswith("http"):
        return url
    return _url(base, url)


def guide_with_build(base, qid, polish=True, on_log=None):
    """widget.html askAbout() over HTTP."""
    detail = question_detail(base, qid)
    if detail.get("buildable") and not detail.get("pdf_url"):
        start_build(base, qid)
        poll_build(base, on_log=on_log)
        detail = question_detail(base, qid)
    ans = render_guide(base, qid, polish=polish)
    ans["pdf_url"] = detail.get("pdf_url") or ans.get("pdf_url")
    ans["video_url"] = detail.get("video_url") or ans.get("video_url")
    ans["quality"] = detail.get("quality") or ans.get("quality")
    ans["buildable"] = detail.get("buildable")
    return ans


def chat_with_build(base, message, polish=True, on_log=None):
    """widget.html send() over HTTP."""
    resp = chat(base, message, polish=polish)
    qid = resp.get("qid")
    guides = resp.get("guides") or ([qid] if qid else [])
    buildable = resp.get("buildable")
    if qid and buildable is None:
        buildable = bool(qid)
    if (not qid or resp.get("action") in ("clarify", "none") or not buildable):
        return resp
    if resp.get("pdf_url") or resp.get("video_url"):
        return resp
    try:
        start_build(base, qid, request_text=message,
                    guides=guides if len(guides) > 1 else None)
        st = poll_build(base, on_log=on_log)
        out = (st or {}).get("output") or {}
        if out.get("not_found"):
            resp["answer"] = resp.get("answer", "") + "\n\n⚠ " + out.get("message", "")
        else:
            resp["pdf_url"] = out.get("pdf") or resp.get("pdf_url")
            resp["video_url"] = out.get("video") or resp.get("video_url")
        if not resp.get("pdf_url"):
            detail = question_detail(base, qid)
            resp["pdf_url"] = detail.get("pdf_url")
            resp["video_url"] = detail.get("video_url")
    except urllib.error.URLError as e:
        resp["build_error"] = "Backend build failed: %s" % e
    return resp
