"""
backend/config.py
All settings loaded from environment variables via pydantic BaseSettings.
Never hardcode API keys or model names — always use settings.*
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── OpenRouter ────────────────────────────────────────────────────────────
    openrouter_api_key: str = ""

    # ── Supabase ──────────────────────────────────────────────────────────────
    supabase_url: str = ""
    supabase_service_key: str = ""

    # ── Web Search ────────────────────────────────────────────────────────────
    serper_api_key: str = ""

    # ── Pipeline Tuning ───────────────────────────────────────────────────────
    pipeline_max_retrieved_docs: int = 12
    pipeline_rerank_top_k: int = 6
    pipeline_max_claims: int = 10
    pipeline_verification_threshold: float = 0.7

    # ── Models ────────────────────────────────────────────────────────────────
    model_intent: str = "mistralai/mistral-7b-instruct:free"
    model_generation: str = "google/gemma-3-27b-it:free"
    model_verification: str = "google/gemma-3-12b-it:free"
    model_arithmetic: str = "mistralai/mistral-7b-instruct:free"

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: str = "development"
    pipeline_version: str = "v1.0.0"

    # ── CORS ──────────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


# Singleton — import this everywhere
settings = Settings()
