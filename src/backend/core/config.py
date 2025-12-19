"""
Application configuration using Pydantic Settings.

All configuration is loaded from environment variables or Azure Key Vault.
"""

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "TruePulse"
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = ""  # Required - loaded from environment

    # Azure
    AZURE_TENANT_ID: str | None = None
    AZURE_CLIENT_ID: str | None = None
    AZURE_KEY_VAULT_URL: str | None = None

    # Database - PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "truepulse"
    POSTGRES_PASSWORD: str = ""  # Required - loaded from environment
    POSTGRES_DB: str = "truepulse"

    @field_validator("SECRET_KEY", "POSTGRES_PASSWORD", "FRONTEND_API_SECRET")
    @classmethod
    def validate_required_secrets(cls, v: str, info: Any) -> str:
        """Validate that required secrets are set."""
        if not v:
            raise ValueError(f"{info.field_name} must be set in environment")
        return v

    @property
    def POSTGRES_URL(self) -> str:
        """Construct PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Azure Storage (Tables for votes, token blacklist, reset tokens)
    AZURE_STORAGE_ACCOUNT_NAME: str | None = None
    AZURE_STORAGE_TABLE_ENDPOINT: str | None = None
    AZURE_STORAGE_BLOB_URL: str | None = None
    AZURE_STORAGE_CONNECTION_STRING: str | None = None  # For local dev only

    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: str | None = None
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o-mini"
    AZURE_OPENAI_API_KEY: str | None = None

    # AI / Microsoft Foundry (legacy - deprecated)
    FOUNDRY_PROJECT_ENDPOINT: str | None = None
    FOUNDRY_MODEL_DEPLOYMENT: str = "gpt-4o-mini"

    # Azure Communication Services (SMS)
    AZURE_COMMUNICATION_CONNECTION_STRING: str | None = None
    AZURE_COMMUNICATION_SENDER_NUMBER: str | None = None
    SMS_VERIFICATION_CODE_EXPIRY_MINUTES: int = 10

    # Authentication
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    
    # Frontend-only API access
    # Secret shared between frontend and backend to prevent unauthorized API access
    FRONTEND_API_SECRET: str = ""  # Required - loaded from environment
    # Allowed origins for API requests (stricter than CORS - blocks non-browser requests)
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]
    # Whether to enforce frontend-only access (disable for local development if needed)
    ENFORCE_FRONTEND_ONLY: bool = True

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # News API Configuration
    NEWSDATA_API_KEY: str | None = None
    NEWSAPI_ORG_API_KEY: str | None = None

    # Poll Configuration
    POLL_DURATION_HOURS: int = 1  # Duration of each poll in hours (default: 1 hour)
    POLL_AUTO_GENERATE: bool = True  # Automatically generate polls at the start of each period
    POLL_TIMEZONE: str = "UTC"  # Timezone for poll scheduling

    # Platform Statistics Cache
    STATS_CACHE_TTL_HOURS: int = 24  # How often to refresh platform stats (default: 24 hours)

    # Feature Flags
    ENABLE_AI_POLL_GENERATION: bool = True
    ENABLE_GAMIFICATION: bool = True

    # Google AdSense
    ADSENSE_ENABLED: bool = False
    ADSENSE_PUBLISHER_ID: str | None = None
    ADSENSE_AD_SLOT_BANNER: str | None = None
    ADSENSE_AD_SLOT_SIDEBAR: str | None = None
    ADSENSE_AD_SLOT_INTERSTITIAL: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    # Settings are loaded from environment variables via pydantic-settings
    return Settings()


settings = get_settings()
