import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SCHEDULES_FILE = DATA_DIR / "schedules.json"
PENDING_EXTRACTION_FILE = DATA_DIR / "_pending_extraction.json"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev-secret-change-me")

EXTRACTION_MODEL = "gemini-3.6-flash"
QUERY_MODEL = "gemini-3.6-flash"
