# ─────────────────────────────────────────────────────────────────
#  run_pipeline.py  —  one command for Q1:
#     capture  →  PDF + video  →  ingest into RAG
#
#  From the project folder (dish_doc_automation/):
#     python run_pipeline.py             # headed (watch the browser)
#     python run_pipeline.py --headless
#     python run_pipeline.py --skip-capture   # reuse manifest, regen PDF/video
# ─────────────────────────────────────────────────────────────────
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from capture import playwright_agent
from generate import doc_generator

ap = argparse.ArgumentParser()
ap.add_argument("--headless", action="store_true")
ap.add_argument("--skip-capture", action="store_true",
                help="reuse existing manifest, just regenerate PDF/video")
args = ap.parse_args()

if not args.skip_capture:
    print("=" * 60, "\n LAYER 1 — capture\n" + "=" * 60)
    playwright_agent.main(headless=args.headless)

print("\n" + "=" * 60, "\n LAYER 2 — PDF + video\n" + "=" * 60)
doc_generator.main()

try:
    print("\n" + "=" * 60, "\n LAYER 3 — RAG ingest\n" + "=" * 60)
    from rag.rag_engine import ingest_manifest, collection_stats
    from config.settings import BASE_OUT
    ingest_manifest(f"{BASE_OUT}/manifest_enriched.json",
                    workflow_title="Adding a product and assigning it to a menu")
    print("Stats:", collection_stats())
except Exception as e:
    print(f"ℹ️ RAG ingest skipped: {e}")

print("\n🎉 Done. PDF → output/docs,  video → output/videos.")
