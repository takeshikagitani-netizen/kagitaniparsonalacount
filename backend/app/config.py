"""Application configuration."""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "sqlite:///./data/receipts.db"

    # Storage
    storage_path: str = "./storage"

    # Upload limits
    max_upload_size_mb: int = 10

    # OCR settings
    ocr_language: str = "jpn+eng"

    # LLM settings (optional)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    use_llm_for_classification: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
