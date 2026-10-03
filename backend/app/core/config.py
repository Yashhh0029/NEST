import json
import logging
import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    PROJECT_NAME: str = "NEST - AI Community Matching Platform"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api"
    ENABLE_DOCS: bool = True

    # Database
    DATABASE_URL: str = "postgresql://postgres@127.0.0.1:5433/nest_db"

    # Security & JWT
    JWT_SECRET: str = "nest_dev_insecure_jwt_secret_change_in_production_key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # CORS & Domains
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
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
    EMAIL_PROVIDER: str = "smtp"  # "smtp", "brevo", "resend", "sendgrid", "test"
    EMAIL_FROM: str = "NEST Verification <onboarding@resend.dev>"
    EMAIL_FROM_NAME: str = "NEST"
    BREVO_API_KEY: str = ""
    EMAIL_API_KEY: str = ""
    RESEND_API_KEY: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = True
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    EMAIL_RESEND_COOLDOWN_SECONDS: int = 60

    # Nearby Community Notifications (Default radius: 5.0 km)
    NEARBY_COMMUNITY_NOTIFICATION_RADIUS_KM: float = 5.0

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    @field_validator("GOOGLE_CLIENT_ID", mode="before")
    @classmethod
    def clean_client_id(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().strip("'\"")
        return v

    @field_validator(
        "EMAIL_FROM",
        "EMAIL_FROM_NAME",
        "BREVO_API_KEY",
        "RESEND_API_KEY",
        "EMAIL_API_KEY",
        mode="before",
    )
    @classmethod
    def clean_email_settings(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().strip("'\"")
        return v

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    parsed = json.loads(v_stripped)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            return [i.strip() for i in v_stripped.split(",") if i.strip()]
        elif isinstance(v, list):
            return [str(i).strip() for i in v if str(i).strip()]
        return []

    def model_post_init(self, __context):
        # Auto-include FRONTEND_URL in CORS origins if specified
        if self.FRONTEND_URL:
            normalized_front = self.FRONTEND_URL.rstrip("/")
            if normalized_front and normalized_front not in self.BACKEND_CORS_ORIGINS:
                self.BACKEND_CORS_ORIGINS.append(normalized_front)

        # Production safety warning for JWT_SECRET
        if self.ENVIRONMENT == "production":
            if "insecure" in self.JWT_SECRET.lower() or len(self.JWT_SECRET) < 32:
                logger.warning(
                    "SECURITY WARNING: Running in production with default/short JWT_SECRET! "
                    "Ensure JWT_SECRET is overridden with a strong 256-bit secret."
                )

        # Sync RESEND_API_KEY and EMAIL_API_KEY
        if self.RESEND_API_KEY and not self.EMAIL_API_KEY:
            self.EMAIL_API_KEY = self.RESEND_API_KEY
        elif self.EMAIL_API_KEY and not self.RESEND_API_KEY:
            self.RESEND_API_KEY = self.EMAIL_API_KEY

        # If API key is present and provider is still default smtp without host, auto-select provider
        if self.BREVO_API_KEY and self.EMAIL_PROVIDER == "smtp" and not self.SMTP_HOST:
            self.EMAIL_PROVIDER = "brevo"
        elif self.EMAIL_API_KEY and self.EMAIL_PROVIDER == "smtp" and not self.SMTP_HOST:
            self.EMAIL_PROVIDER = "resend"

        # In sandbox/fallback, if using Resend and default placeholder domain, fallback to Resend sandbox sender
        if self.EMAIL_PROVIDER == "resend" and (not self.EMAIL_FROM or "noreply@nest-community.org" in self.EMAIL_FROM):
            self.EMAIL_FROM = "NEST Verification <onboarding@resend.dev>"


settings = Settings()

