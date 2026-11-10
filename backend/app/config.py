from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent
APP_DIR = Path(__file__).resolve().parent
ML_DIR = BASE_DIR / "ml"
ARTIFACTS_DIR = ML_DIR / "artifacts"
CATALOG_PATH = APP_DIR / "catalog.json"
FEATURES_PATH = ML_DIR / "features.json"
WEB_DIR = BASE_DIR / "web"
WIDGET_DIR = BASE_DIR / "widget"
ASSETS_DIR = APP_DIR / "assets"
DIGITS_DIR = ASSETS_DIR / "digits"
DATA_DIR = BASE_DIR / "data"

CAPTCHA_TEST_MODE = os.environ.get("CAPTCHA_TEST_MODE", "0") == "1"
HMAC_SECRET = os.environ.get("CAPTCHA_HMAC_SECRET", "adaptive-captcha-dev-secret-key-change-in-prod")
TOKEN_TTL_SECONDS = 120
SESSION_TTL_SECONDS = 300
MAX_ATTEMPTS = 3
MIN_INTERACTION_MS = 400
DEFAULT_BREACH_COST = 2.0

