from pathlib import Path
from pydantic import field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "AutoApplyAI"

    ENVIRONMENT: str = "dev"

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = ["dev", "staging", "prod"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    DEBUG: bool = True

    APP_HOST: str = "0.0.0.0"

    APP_PORT: int = 8000

    API_V1_PREFIX: str = "/api/v1"

    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    DATABASE_URL: str

    REDIS_URL: str

    JWT_ALGORITHM: str = "HS256"

    JWT_SECRET_KEY: SecretStr

    JWT_REFRESH_SECRET_KEY: SecretStr

    @field_validator("JWT_SECRET_KEY", "JWT_REFRESH_SECRET_KEY")
    @classmethod
    def validate_secret_length(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < 32:
            raise ValueError("JWT secrets must be at least 32 characters")
        return v

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    COOKIE_SECURE: bool = False

    COOKIE_HTTP_ONLY: bool = True

    COOKIE_SAMESITE: str = "lax"

    OPENAI_API_KEY: SecretStr = SecretStr("")

    GEMINI_API_KEY: SecretStr = SecretStr("")

    OPENAI_MODEL: str = "gpt-5.4-mini"

    GEMINI_MODEL: str = "gemini-2.5-flash"

    OPENROUTER_API_KEY: SecretStr = SecretStr("")

    OPENROUTER_MODEL: str = "openai/gpt-5.4-mini"

    ANTHROPIC_API_KEY: SecretStr = SecretStr("")

    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

    N8N_WEBHOOK_URL: str = ""

    N8N_WEBHOOK_TIMEOUT_SECONDS: float = 3.0

    AWS_ACCESS_KEY_ID: SecretStr = SecretStr("")

    AWS_SECRET_ACCESS_KEY: SecretStr = SecretStr("")

    AWS_REGION: str = "ap-south-1"

    S3_BUCKET_NAME: str = ""

    PLAYWRIGHT_HEADLESS: bool = True

    CELERY_BROKER_URL: str

    CELERY_RESULT_BACKEND: str

    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
