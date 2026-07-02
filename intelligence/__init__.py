"""
intelligence/ - the self-improving layer for the DISH documentation automation.

The system follows a SEE -> PLAN -> VERIFY -> LEARN loop:

  resolver.py     SEE    - find on-screen elements by *meaning* ("the edit pencil"),
                           try ranked strategies, remember what worked (self-healing).
  autorecipe.py   PLAN   - turn an official PDF/HTML into a step script automatically.
  verify.py       VERIFY - after capture, self-check every frame and flag failures.
  feedback.py     LEARN  - collect thumbs up/down, promote good selectors, flag bad steps.
  monitor.py             - detect UI drift by diffing fresh screenshots vs the last good build.
  llm.py                 - the pluggable "brain": add a model key and the vision/planning
                           parts switch on automatically. No key => graceful heuristics.
  orchestrator.py        - one entry point: PDF -> build -> verify -> report.

Nothing here needs a model to run; adding one in config/intelligence.json upgrades it.
"""
__all__ = ["resolver", "verify", "autorecipe", "feedback", "monitor", "llm", "orchestrator"]
