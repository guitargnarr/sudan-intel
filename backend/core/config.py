"""Configuration management for Sudan Intel platform."""

from typing import List, Optional

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "Sudan Intel"
    VERSION: str = "0.1.0"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./sudan_intel.db"

    # Server
    PORT: int = 8900
    CORS_ORIGINS: str = "http://localhost:5199,http://localhost:3000,http://localhost:5203,https://sudan-intel.vercel.app"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # Data source identifiers (loaded from .env)
    HDX_APP_IDENTIFIER: str = ""
    ACLED_TOKEN: Optional[str] = None
    ACLED_EMAIL: Optional[str] = None
    RELIEFWEB_APPNAME: Optional[str] = None

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "sudan-intel-analyst"
    OLLAMA_FALLBACK_MODEL: str = "qwen2.5:7b"

    # Ingestion intervals (hours)
    HDX_INTERVAL_HOURS: int = 6
    GDELT_INTERVAL_MINUTES: int = 30
    UNHCR_INTERVAL_HOURS: int = 24
    SYNTHESIS_INTERVAL_HOURS: int = 6

    # Logging
    LOG_LEVEL: str = "INFO"


settings = Settings()
