"""
Application settings loaded from environment variables.
"""
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

load_dotenv(dotenv_path=ENV_FILE)


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        case_sensitive=True,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "sqlite:///./gem_ai.db"
    TURSO_DATABASE_URL: str = ""
    TURSO_AUTH_TOKEN: str = ""

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # OpenRouter
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    OPENROUTER_GENERAL_MODEL: str = "qwen/qwen3-coder:free"
    OPENROUTER_CODING_MODEL: str = "qwen/qwen3-coder"
    OPENROUTER_FREE_FALLBACK_MODEL: str = "nvidia/nemotron-3-nano-30b-a3b:free"
    OPENROUTER_FALLBACK_PROVIDERS: str = "nvidia"
    OPENROUTER_MAX_TOKENS: int = 4096
    OPENROUTER_TIMEOUT_SECONDS: int = 45
    OPENROUTER_HTTP_REFERER: str = "http://localhost:5173"
    OPENROUTER_APP_TITLE: str = "Gem-AI"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_SENDER_EMAIL: str = ""
    GOOGLE_APP_PASSWORD: str = ""
    OTP_EXPIRY_MINUTES: int = 10
    OTP_LENGTH: int = 6

    # App
    APP_NAME: str = "Gem-AI"
    DEBUG: bool = True
    CORS_ORIGINS: list[str] = DEFAULT_CORS_ORIGINS

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def normalize_cors_origins(cls, value: Any) -> list[str]:
        """Allow CORS origins to be provided as a CSV string or list."""
        if value is None:
            return list(DEFAULT_CORS_ORIGINS)
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, (list, tuple, set)):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        raise ValueError("CORS_ORIGINS must be a comma-separated string or a list")


settings = Settings()
