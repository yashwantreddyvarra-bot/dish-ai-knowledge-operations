"""
llm.py - the pluggable "brain".

This is the ONE place you upgrade the system's intelligence. Drop a model key into
config/intelligence.json (or set an env var) and the vision + planning features across
the package turn on automatically. With no key, every caller degrades to heuristics, so
the pipeline always runs.

config/intelligence.json (optional):
{
  "provider": "anthropic",          // "anthropic" | "openai" | "none"
  "api_key": "sk-...",              // or leave blank and set ANTHROPIC_API_KEY / OPENAI_API_KEY
  "text_model": "claude-3-5-sonnet-latest",
  "vision_model": "claude-3-5-sonnet-latest"
}

"Upgrading the neural network" = changing these model names, or switching provider, or
pointing text_model/vision_model at a fine-tuned model trained on your feedback data.
"""
import os, json, base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = ROOT / "config" / "intelligence.json"


def _config():
    cfg = {"provider": "none", "api_key": "", "text_model": "", "vision_model": ""}
    try:
        cfg.update(json.loads(CFG.read_text(encoding="utf-8")))
    except Exception:
        pass
    if not cfg.get("api_key"):
        cfg["api_key"] = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
        if os.getenv("ANTHROPIC_API_KEY"):
            cfg["provider"] = "anthropic"
        elif os.getenv("OPENAI_API_KEY"):
            cfg["provider"] = "openai"
    return cfg


def available():
    """True if a model is configured. Callers use heuristics when this is False."""
    c = _config()
    return bool(c.get("api_key")) and c.get("provider", "none") != "none"


def ask_text(prompt, system=None, max_tokens=1500):
    """Single-shot text completion. Returns the model's text, or None if no model/error."""
    c = _config()
    if not available():
        return None
    try:
        if c["provider"] == "anthropic":
            import anthropic
            cl = anthropic.Anthropic(api_key=c["api_key"], timeout=20.0, max_retries=1)  # fail fast, never hang the chat
            msg = cl.messages.create(
                model=c.get("text_model") or "claude-3-5-sonnet-latest",
                max_tokens=max_tokens, system=system or "",
                messages=[{"role": "user", "content": prompt}])
            return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        if c["provider"] == "openai":
            from openai import OpenAI
            cl = OpenAI(api_key=c["api_key"], timeout=20.0, max_retries=1)  # fail fast, never hang the chat
            r = cl.chat.completions.create(
                model=c.get("text_model") or "gpt-4o",
                messages=[m for m in [{"role": "system", "content": system}] if system] +
                         [{"role": "user", "content": prompt}],
                max_tokens=max_tokens)
            return r.choices[0].message.content
    except Exception as e:
        print("llm.ask_text error:", str(e)[:120])
    return None


def ask_vision(prompt, image_path, system=None, max_tokens=600):
    """Ask a question about an image (e.g. 'does this frame show the pencil being clicked?').
    Returns text, or None if no vision model/error."""
    c = _config()
    if not available():
        return None
    try:
        data = base64.b64encode(Path(image_path).read_bytes()).decode()
        if c["provider"] == "anthropic":
            import anthropic
            cl = anthropic.Anthropic(api_key=c["api_key"], timeout=20.0, max_retries=1)  # fail fast, never hang the chat
            msg = cl.messages.create(
                model=c.get("vision_model") or "claude-3-5-sonnet-latest",
                max_tokens=max_tokens, system=system or "",
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}},
                    {"type": "text", "text": prompt}]}])
            return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        if c["provider"] == "openai":
            from openai import OpenAI
            cl = OpenAI(api_key=c["api_key"], timeout=20.0, max_retries=1)  # fail fast, never hang the chat
            r = cl.chat.completions.create(
                model=c.get("vision_model") or "gpt-4o",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + data}}]}],
                max_tokens=max_tokens)
            return r.choices[0].message.content
    except Exception as e:
        print("llm.ask_vision error:", str(e)[:120])
    return None


def status():
    c = _config()
    return {"model_available": available(), "provider": c.get("provider"),
            "text_model": c.get("text_model"), "vision_model": c.get("vision_model")}
