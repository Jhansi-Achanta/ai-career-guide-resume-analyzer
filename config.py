"""Central configuration for the AI Career Guide & Resume Analyzer.

Every setting (and the Gemini API key) is read from the ".env" file that sits
next to this file.  Nothing secret is ever hard-coded here, and the key is
never sent to the browser.

Usage::

    import config
    print(config.GEMINI_MODEL)
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

# Load variables from ".env" (the file is optional - the app still starts).
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"

ANALYSES_FILE = DATA_DIR / "analyses.json"
CAREER_PLANS_FILE = DATA_DIR / "career_plans.json"

# ---------------------------------------------------------------------------
# Gemini / AI settings
# ---------------------------------------------------------------------------
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()

# Current stable, fast, general-purpose Gemini model.
# Older ids such as "gemini-2.0-flash" have been shut down, so the model name
# is kept in ".env" and can be changed without editing any Python code.
GEMINI_MODEL = (os.getenv("GEMINI_MODEL") or "gemini-3.8-flash-lite").strip()

# True only when a key is present.  The UI shows a friendly notice instead of
# the app crashing when the key is missing.
AI_CONFIGURED = bool(GEMINI_API_KEY)

# ---------------------------------------------------------------------------
# Upload / request limits
# ---------------------------------------------------------------------------
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB") or 5)
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# Only these resume formats are accepted.
ALLOWED_EXTENSIONS = {".pdf", ".docx"}

# A resume shorter than this is almost certainly empty, or a scanned image
# with no selectable text.
MIN_RESUME_CHARS = 120

# How much resume text is handed to the model (keeps prompts small and fast).
MAX_RESUME_CHARS = 15000

# ---------------------------------------------------------------------------
# Flask server
# ---------------------------------------------------------------------------
HOST = (os.getenv("HOST") or "127.0.0.1").strip()
PORT = int(os.getenv("PORT") or 5000)
DEBUG = (os.getenv("FLASK_DEBUG") or "1").strip().lower() not in {"0", "false", "no"}
