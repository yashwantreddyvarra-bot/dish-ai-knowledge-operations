# The intelligence layer

This makes the documentation automation **adaptive and self-improving** instead of a fixed
script. It runs today on heuristics; add a model key and the vision/planning parts switch on.

## The loop

```
 SEE  ──► PLAN ──► CAPTURE ──► BUILD ──► VERIFY ──► LEARN ──┐
  ▲                                                          │
  └──────────────── feedback + drift monitor ◄───────────────┘
```

| Stage | File | What it does |
|-------|------|--------------|
| SEE | `resolver.py` | Finds elements by *meaning* (`edit_pencil`, `save_button`). Ranks selector strategies by what worked before and remembers winners → self-healing. |
| PLAN | `autorecipe.py` | Turns an official PDF/HTML into a step script **and** a capture plan automatically. |
| VERIFY | `verify.py` | After each build, self-checks every frame (blank / duplicate / missing box / caption mismatch) and prints a 0–100 score + flagged steps. |
| LEARN | `feedback.py` | Stores 👍/👎, reinforces good selectors, flags weak steps for rebuild. |
| DRIFT | `monitor.py` | Diffs fresh frames vs a baseline; detects when DISH changes a screen. |
| BRAIN | `llm.py` | The one place to add a model key. No key → heuristics. |
| RUN | `orchestrator.py` | `make_from_pdf(qid, pdf)` = plan → capture → build → verify → report. |

## Use it

```
smart_build.bat 11 "C:\path\to\official_Q11.pdf"   # auto plan+capture+build+self-check
verify_all.bat                                     # score every built question
python -m intelligence.orchestrator health         # status of the whole layer
python -m intelligence.monitor                     # drift report
```

## Upgrading the "neural network"

1. Put a key in `config/intelligence.json` (provider `anthropic` or `openai`). Vision
   verification (`verify.py`) and LLM planning (`autorecipe.py`, `resolver.locate_with_vision`)
   activate automatically — the system starts *seeing* screens instead of guessing selectors.
2. As you collect 👍/👎, `output/feedback.json` + `output/resolver_cache.json` become a
   training set: page state → target → selector that worked → human rating. Fine-tune a small
   model on that and point `text_model`/`vision_model` at it. That is the realistic,
   non-magical version of "it upgrades its own neural net".

No "consciousness" required — just see → plan → verify → learn, getting more reliable every run.
