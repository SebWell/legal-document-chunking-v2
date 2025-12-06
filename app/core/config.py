"""
Configuration application.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from functools import lru_cache
import json


class Settings(BaseSettings):
    """Configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # Ignore extra environment variables
    )

    # Environment
    ENV: str = "development"
    DEBUG: bool = True

    # API
    API_VERSION: str = "4.1.0"
    API_TITLE: str = "ChantierDoc Document Chunking API (PyMuPDF/PaddleOCR)"

    # Authentication
    API_SECRET_KEY: str = ""

    # Timeouts (en secondes)
    REQUEST_TIMEOUT: int = 180        # 3 minutes max par requête
    PROCESSING_TIMEOUT: int = 120     # 2 minutes max pour processing

    # Security
    ALLOWED_ORIGINS: str = '["http://localhost:3000"]'
    ALLOWED_HOSTS: str = '["localhost"]'

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 10

    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.ENV == "development"

    def get_allowed_origins(self) -> List[str]:
        """Parse ALLOWED_ORIGINS from JSON string."""
        try:
            return json.loads(self.ALLOWED_ORIGINS)
        except json.JSONDecodeError:
            return ["http://localhost:3000"]

    def get_allowed_hosts(self) -> List[str]:
        """Parse ALLOWED_HOSTS from JSON string."""
        try:
            return json.loads(self.ALLOWED_HOSTS)
        except json.JSONDecodeError:
            return ["localhost"]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
