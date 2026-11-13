"""Configuration de l'application Talk-Translate."""

import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(
    os.environ.get("TALK_TRANSLATE_DATABASE", BASE_DIR / "instance" / "talk_translate.sqlite3")
)
MAX_TEXT_LENGTH = 500
MAX_TTS_LENGTH = 2000
HISTORY_LIMIT = 50
RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW_SECONDS = 60
TRANSLATION_CACHE_SIZE = 256
TTS_CACHE_SIZE = 64
MAX_CONTENT_LENGTH = 16 * 1024
DEBUG = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
SECRET_KEY = os.environ.get("SECRET_KEY")
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "").lower() in {"1", "true", "yes"}
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
PERMANENT_SESSION_LIFETIME = timedelta(days=365)
TRUST_PROXY = os.environ.get("TRUST_PROXY", "").lower() in {"1", "true", "yes"}
