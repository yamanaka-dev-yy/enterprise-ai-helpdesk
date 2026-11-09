import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    database: str = os.getenv("DATABASE_PATH", str(ROOT / "data/helpdesk.sqlite3"))
    secure_cookie: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    demo: bool = os.getenv("ENABLE_DEMO", "true").lower() == "true"
    llm_url: str = os.getenv("LLM_BASE_URL", "").rstrip("/")
    llm_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "helpdesk-model")
    llm_read_timeout: int = max(5, min(60, int(os.getenv("LLM_READ_TIMEOUT_SECONDS", "45"))))
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "")
    ai_daily_limit: int = max(0, int(os.getenv("AI_DAILY_LIMIT", "30")))
    session_ai_limit: int = max(0, int(os.getenv("SESSION_AI_LIMIT", "8")))
    input_price: str = os.getenv("INPUT_USD_PER_MILLION", "")
    output_price: str = os.getenv("OUTPUT_USD_PER_MILLION", "")
    admin_email: str = os.getenv("ADMIN_EMAIL", "")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    employee_email: str = os.getenv("EMPLOYEE_EMAIL", "")
    employee_password: str = os.getenv("EMPLOYEE_PASSWORD", "")
