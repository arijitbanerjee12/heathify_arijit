"""
Configuration module — loads environment variables and sets defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ------------------------------------------------------------------
# Required secrets
# ------------------------------------------------------------------
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ------------------------------------------------------------------
# LLM settings
# ------------------------------------------------------------------
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# Preset configurations for different use-cases
LLM_PRESETS = {
    "classify": {
        "temperature": 0.2,
        "max_completion_tokens": 256,
        "reasoning_effort": "low",
    },
    "coach": {
        "temperature": 0.5,
        "max_completion_tokens": 512,
        "reasoning_effort": "medium",
    },
    "summarize": {
        "temperature": 0.4,
        "max_completion_tokens": 1024,
        "reasoning_effort": "medium",
    },
}

# ------------------------------------------------------------------
# Rate limits (GPT OSS 120B via Groq)
# ------------------------------------------------------------------
RATE_LIMIT_RPM: int = 30        # requests per minute
RATE_LIMIT_RPD: int = 1000      # requests per day
RATE_LIMIT_TPM: int = 8000      # tokens per minute
RATE_LIMIT_TPD: int = 200_000   # tokens per day

# ------------------------------------------------------------------
# Database
# ------------------------------------------------------------------
ROOT_DIR = Path(__file__).parent.absolute()
_default_db = str(ROOT_DIR / "data" / "healthy_agent.db")
DB_PATH: str = os.getenv("DB_PATH", _default_db)

# Ensure the data directory exists
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# Timezone
# ------------------------------------------------------------------
USER_TIMEZONE: str = os.getenv("USER_TIMEZONE", "Asia/Kolkata")

# ------------------------------------------------------------------
# Streamlit
# ------------------------------------------------------------------
STREAMLIT_PORT: int = int(os.getenv("STREAMLIT_PORT", "8501"))

# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------
def validate_config() -> list[str]:
    """Return list of missing required config keys."""
    missing = []
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    return missing
