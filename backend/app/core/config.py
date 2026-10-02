import os
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "NEST - AI Community Matching Platform"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api"

    # Database
    DATABASE_URL: str = "postgresql://postgres@127.0.0.1:5433/nest_db"

    # Security & JWT
    JWT_SECRET: str = "nest_dev_insecure_jwt_secret_change_in_production_key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # CORS
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # ML Embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # Google Maps Platform (Phase 6 Location Intelligence)
    GOOGLE_MAPS_SERVER_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""  # Fallback for backward compatibility

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Transactional Email (Email Verification)
    EMAIL_PROVIDER: str = "smtp"  # "smtp", "resend", "sendgrid", "test"
    EMAIL_FROM: str = "NEST Community <noreply@nest-community.org>"
    EMAIL_API_KEY: str = ""
    RESEND_API_KEY: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = True
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    EMAIL_RESEND_COOLDOWN_SECONDS: int = 60

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def model_post_init(self, __context):
        # Sync RESEND_API_KEY and EMAIL_API_KEY
        if self.RESEND_API_KEY and not self.EMAIL_API_KEY:
            self.EMAIL_API_KEY = self.RESEND_API_KEY
        elif self.EMAIL_API_KEY and not self.RESEND_API_KEY:
            self.RESEND_API_KEY = self.EMAIL_API_KEY

        # If API key is present and provider is still default smtp without host, auto-select resend
        if self.EMAIL_API_KEY and self.EMAIL_PROVIDER == "smtp" and not self.SMTP_HOST:
            self.EMAIL_PROVIDER = "resend"

        # If resend is active and EMAIL_FROM has unverified domain, default to Resend sandbox sender
        if self.EMAIL_PROVIDER == "resend" and "noreply@nest-community.org" in self.EMAIL_FROM:
            self.EMAIL_FROM = "NEST Verification <onboarding@resend.dev>"


settings = Settings()

