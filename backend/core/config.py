import os
from dotenv import load_dotenv

load_dotenv(override=True)         # ✅ module level, not inside class

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

    # ─── AI & LLM Models (NEW INTEGRATION) ────────────────────────
    # 1. Cloudflare Workers AI
    CLOUDFLARE_API_KEY:    str = os.getenv("CLOUDFLARE_API_KEY", "")
    CLOUDFLARE_ACCOUNT_ID: str = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    CF_MODEL_REASONING: str = os.getenv("CF_MODEL_REASONING", "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b")
    CF_MODEL_STORY:     str = os.getenv("CF_MODEL_STORY",     "@cf/meta/llama-3.3-70b-instruct-fp8-fast")
    CF_MODEL_FAST:      str = os.getenv("CF_MODEL_FAST",      "@cf/meta/llama-3.3-70b-instruct-fp8-fast")
    
    # 2. OpenRouter Multi-Model (All-In-One API)
    OPENROUTER_API_KEY:    str = os.getenv("OPENROUTER_API_KEY", "")
    MODEL_REASONING:       str = os.getenv("MODEL_REASONING", "deepseek/deepseek-r1:free")
    MODEL_WRITER:          str = os.getenv("MODEL_WRITER", "meta-llama/llama-3.3-70b-instruct:free")
    MODEL_FAST:            str = os.getenv("MODEL_FAST", "google/gemini-2.5-flash:free")
    OPENROUTER_MODEL:      str = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-r1:free")
    
    # 3. Story Learning Engine Tiers
    STORY_MODEL_PREFERENCE: str = os.getenv("STORY_MODEL_PREFERENCE", "meta-llama/llama-3.3-70b-instruct:free")
    PROMPT_HUMANIZER_TIER:  str = os.getenv("PROMPT_HUMANIZER_TIER", "deepseek/deepseek-r1:free")
    
    # 4. GitHub Actions CI/CD (GitHub Models API)
    GH_MODELS_TOKEN:       str = os.getenv("GH_MODELS_TOKEN", "")
    GH_MODEL_REASONING: str = os.getenv("GH_MODEL_REASONING", "gpt-4o-mini")  # ឬ o1-mini ទៅតាមតារាង mapping
    GH_MODEL_STORY:     str = os.getenv("GH_MODEL_STORY",     "gpt-4o")
    GH_MODEL_WRITER:    str = os.getenv("GH_MODEL_WRITER",    "gpt-4o")

settings = Settings()
