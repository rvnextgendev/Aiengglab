"""Validated settings; secrets are never hard-coded."""
from functools import lru_cache
from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    database_url: str | None = None
    jwt_secret: SecretStr
    jwt_issuer: str = "arinova-local"
    jwt_audience: str = "arinova-api"
    log_level: str = "INFO"

    @model_validator(mode="after")
    def validate_security(self):
        if self.app_env not in {"development", "test", "production"}:
            raise ValueError("Invalid APP_ENV")
        if len(self.jwt_secret.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        if self.app_env == "production" and not self.database_url:
            raise ValueError("DATABASE_URL required in production")
        return self

@lru_cache
def get_settings() -> Settings:
    return Settings()
