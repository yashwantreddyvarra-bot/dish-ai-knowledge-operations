"""
orchestrator.py - one entry point for the whole self-improving loop.

  make_from_pdf(qid, pdf)  : PLAN (autorecipe) -> CAPTURE (engine) -> BUILD (doc_generator)
                             -> VERIFY (self-check) -> retry weak steps once -> report.

This is the "point it at an official PDF and walk away" pipeline. It self-checks and, when a
model is configured, self-corrects. Without a model it still auto-plans, builds, and reports a
quality score so you instantly see which steps need a human glance - instead of reviewing
every frame by hand.
"""
import json
from pathlib import Path
from . import autorecipe, verify

ROOT = Path(__file__).resolve().parent.parent


def make_from_pdf(qid, pdf_path, do_capture=True):
    print("=" * 60)
    print("AUTO-BUILD Q%02d from %s" % (qid, Path(pdf_path).name))
    n = autorecipe.from_pdf(qid, pdf_path)
    print("PLAN: %d steps + auto capture plan written" % n)

    if do_capture:
        try:
            from capture import engine
            engine.main(qid=qid, headless=False)
        except Exception as e:
            print("capture skipped/failed:", str(e)[:120])
    try:
        from generate import doc_generator
        doc_generator.build(qid)
    except Exception as e:
        print("build failed:", str(e)[:120])

    report = verify.question(qid)
    weak = [s["step"] for s in report.get("steps", []) if s["status"] != "ok"]
    if weak:
        print("NEEDS ATTENTION: steps %s (see output/verify_q%02d.json)" % (weak, qid))
    else:
        print("All steps passed self-check.")
    return report


def health():
    """One-glance status of the intelligence layer."""
    from . import llm, resolver, feedback
    return {"model": llm.status(), "resolver": resolver.stats(),
            "feedback": feedback.summary()}


if __name__ == "__main__":
    import sys
    if sys.argv[1] == "health":
        print(json.dumps(health(), indent=2))
    else:
        make_from_pdf(int(sys.argv[1]), sys.argv[2], do_capture="--nocapture" not in sys.argv)
