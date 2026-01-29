"""Bot configuration."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# First admin username (without @)
FIRST_ADMIN_USERNAME = os.getenv("FIRST_ADMIN_USERNAME", "")

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
QUESTIONS_FILE = DATA_DIR / "questions.json"
DATABASE_PATH = BASE_DIR / "bot_database.db"
GENERATED_DOCS_DIR = BASE_DIR / "generated_docs"

# Fingerprint server settings
FINGERPRINT_SERVER_PORT = int(os.getenv("FINGERPRINT_SERVER_PORT", "8080"))
FINGERPRINT_SERVER_URL = os.getenv("FINGERPRINT_SERVER_URL", "https://payport.example.com")

# Ensure directories exist
GENERATED_DOCS_DIR.mkdir(exist_ok=True)

