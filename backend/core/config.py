import os
from dotenv import load_dotenv

load_dotenv(override=True)          # ✅ module level, not inside class


class Settings:

    # ─── App ──────────────────────────────────────────────────────
    APP_NAME: str = os.getenv("APP_NAME", "FWG AI-OS")
    DEBUG: bool   = os.getenv("DEBUG", "true").lower() == "true"
    ENV: str      = os.getenv("ENV", "development")

    # ─── Database ─────────────────────────────────────────────────
    POSTGRES_HOST:     str = os.getenv("POSTGRES_HOST",     "localhost")
    POSTGRES_USER:     str = os.getenv("POSTGRES_USER",     "aios_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "aios_password")
    POSTGRES_DB:       str = os.getenv("POSTGRES_DB",       "aios_db")

    DATABASE_URL: str = os.getenv(        # ✅ SQLite/PostgreSQL flexible
        "DATABASE_URL",
        f"postgresql://{os.getenv('POSTGRES_USER','aios_user')}"
        f":{os.getenv('POSTGRES_PASSWORD','aios_password')}"
        f"@{os.getenv('POSTGRES_HOST','localhost')}"
        f"/{os.getenv('POSTGRES_DB','aios_db')}"
    )

    # ─── Redis ────────────────────────────────────────────────────
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_URL:  str = os.getenv(
        "REDIS_URL",
        f"redis://{os.getenv('REDIS_HOST','localhost')}:{os.getenv('REDIS_PORT','6379')}"
    )

    # ─── Qdrant ───────────────────────────────────────────────────
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_URL:  str = os.getenv(
        "QDRANT_URL",
        f"http://{os.getenv('QDRANT_HOST','localhost')}:{os.getenv('QDRANT_PORT','6333')}"
    )

    # ─── Worker ✅ Dev ────────────────────────────────────────────
    WORKER_HOST: str = os.getenv("WORKER_HOST", "localhost")
    WORKER_PORT: int = int(os.getenv("WORKER_PORT", "8001"))

    # ─── API Keys ─────────────────────────────────────────────────
    YOUTUBE_API_KEY:      str = os.getenv("YOUTUBE_API_KEY",   "")
    APIFY_API_TOKEN:      str = os.getenv("APIFY_API_TOKEN",   "")
    HF_TOKEN:             str = os.getenv("HF_TOKEN",          "")
    AGENT_URL:            str = os.getenv("AGENT_URL",         "https://sereyfwg-agent.hf.space")
    CLOUD_FUNCTION_URL:   str = os.getenv("CLOUD_FUNCTION_URL","")  # ✅ Dev: TikTok


settings = Settings()
