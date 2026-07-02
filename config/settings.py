# ─────────────────────────────────────────────────────────────────
#  config/settings.py  —  central config (paths anchored to project root,
#  so the pipeline works no matter which directory you run it from)
# ─────────────────────────────────────────────────────────────────
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Project root = the folder that contains this config/ package
ROOT = Path(__file__).resolve().parent.parent

# ── URLs ──────────────────────────────────────────────────────────
LOGIN_URL    = os.getenv("LOGIN_URL",    "https://netherlands.sandbox.myplace.dish.co/cm/login")
PRODUCTS_URL = os.getenv("PRODUCTS_URL", "https://netherlands.sandbox.myplace.dish.co/cm/products")
MENUS_URL    = os.getenv("MENUS_URL",    "https://netherlands.sandbox.myplace.dish.co/cm/menus")

# ── Login credentials ─────────────────────────────────────────────
EMAIL    = os.getenv("DISH_EMAIL",    "booq_en_video@dish.digital")
PASSWORD = os.getenv("DISH_PASSWORD", "booq_en_video@dish.digital")

# ── Product to create ─────────────────────────────────────────────
PRODUCT_NAME  = os.getenv("PRODUCT_NAME",  "Sparkling Water")
PRODUCT_PRICE = os.getenv("PRODUCT_PRICE", "3.50")

# ── Current UI selection preferences (verified from front-end) ─────
PRODUCT_CATEGORY_PREF = ["Soft Drinks", "Drinks", "Dranken", "Food", "Miscellaneous"]
VAT_PREF              = ["9%", "9% - Laag", "9% - Low", "Laag", "Low", "9"]
MENU_PREF             = ["Menukaart", "Menu", "Main"]

# Deprecated aliases (old drag-and-drop flow)
PRODUCT_GROUP_PREF = PRODUCT_CATEGORY_PREF
TURNOVER_PREF      = ["Drinks Low VAT", "Low VAT", "Drinks", "Dranken Laag", "Food"]
MENU_NAME          = "Menukaart"
MENU_CATEGORY      = "Drinks"

# ── Output paths (absolute, under project root) ───────────────────
BASE_OUT  = str(ROOT / "output")
SS_DIR    = str(ROOT / "output" / "screenshots")
VIDEO_DIR = str(ROOT / "output" / "videos")
DOCS_DIR  = str(ROOT / "output" / "docs")
DB_DIR    = str(ROOT / "output" / "vector_db")
RECIPE_DIR = str(ROOT / "recipes")

for _d in (SS_DIR, VIDEO_DIR, DOCS_DIR, DB_DIR, RECIPE_DIR):
    os.makedirs(_d, exist_ok=True)

# ── LLM / RAG ─────────────────────────────────────────────────────
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL         = os.getenv("LLM_MODEL", "gpt-4o")
CHROMA_COLLECTION = "dish_docs"
CHUNK_OVERLAP     = 1
