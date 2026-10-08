import re
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.core.email_validator import validate_email_address
from app.models.user import UserRole


class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Full name of the user")
    email: str = Field(..., description="Valid unique email address")
    password: str = Field(..., min_length=8, max_length=128, description="Strong password (at least 8 chars)")
    role: Optional[UserRole] = Field(default=UserRole.NEWCOMER, description="Initial platform role")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Name must be at least 2 characters long")
        return cleaned

    @field_validator("email")
    @classmethod
    def validate_and_normalize_email(cls, v: str) -> str:
        return validate_email_address(v, allow_disposable=False)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one numerical digit")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter")
        return v


class UserLogin(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_and_normalize_email(cls, v: str) -> str:
        return validate_email_address(v, allow_disposable=True)


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    is_active: bool
    deactivated_reason: Optional[str] = None
    google_id: Optional[str] = None
    is_verified: bool
    email_verified: bool = False
    email_verified_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    user_id: Optional[str] = None


class GoogleAuthRequest(BaseModel):
    id_token: Optional[str] = Field(None, description="Google OAuth ID Token from Google Identity Services")
    credential: Optional[str] = Field(None, description="Google One Tap / GIS credential token alias")


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=1, description="Verification token received in email")


class VerifyEmailResponse(BaseModel):
    message: str
    email_verified: bool


class ResendVerificationRequest(BaseModel):
    email: str = Field(..., description="Email address to resend verification link to")

    @field_validator("email")
    @classmethod
    def validate_and_normalize_email(cls, v: str) -> str:
        return validate_email_address(v, allow_disposable=True)


class ResendVerificationResponse(BaseModel):
    message: str
