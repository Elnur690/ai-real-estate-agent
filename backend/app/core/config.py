import os
import secrets
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, extra="ignore", env_file=".env")

    PROJECT_NAME: str = "AI Real Estate Agent SaaS"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", secrets.token_urlsafe(32))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Admin Credentials
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@erma.shop")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "AdminPass2026!Secure")

    # Allowed Domains & CORS
    ALLOWED_HOSTS: list[str] = [
        "realtor.erma.shop",
        "realtor-api.erma.shop",
        "localhost",
        "127.0.0.1",
        "*"
    ]
    BACKEND_CORS_ORIGINS: list[str] = [
        "https://realtor.erma.shop",
        "http://realtor.erma.shop",
        "https://realtor-api.erma.shop",
        "http://realtor-api.erma.shop",
        "http://localhost:23300",
        "http://localhost:23800",
        "http://localhost:3000",
        "*"
    ]

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite+aiosqlite:///./realestate.db"
    )
    SYNC_DATABASE_URL: str = os.getenv(
        "SYNC_DATABASE_URL", "sqlite:///./realestate.db"
    )

    # Redis / Celery
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN", None)

    # Evolution API (WhatsApp)
    EVOLUTION_API_URL: Optional[str] = os.getenv("EVOLUTION_API_URL", "http://evolution:8080")
    EVOLUTION_API_KEY: Optional[str] = os.getenv("EVOLUTION_API_KEY", "42960a4e6597e231787c5e0124a06248")
    EVOLUTION_INSTANCE_NAME: str = os.getenv("EVOLUTION_INSTANCE_NAME", "realestate_agent")
    WEBHOOK_SECRET: Optional[str] = os.getenv("WEBHOOK_SECRET", None)

    # Telegram Scraping (Telethon)
    TELEGRAM_API_ID: Optional[int | str] = None
    TELEGRAM_API_HASH: Optional[str] = os.getenv("TELEGRAM_API_HASH", None)

    # Gemini Fallback Key
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)

settings = Settings()
