import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.email_validator import validate_email_address
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.auth import Token, UserLogin, UserRegister, UserResponse
from app.services.email_service import send_verification_email

logger = logging.getLogger(__name__)


def register_user(db: Session, user_in: UserRegister) -> User:
    """Register a new user after verifying email uniqueness, blocking disposable domains, and hashing password."""
    try:
        norm_email = validate_email_address(user_in.email, allow_disposable=False)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )

    existing_user = db.query(User).filter(User.email == norm_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    hashed_pw = hash_password(user_in.password)
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)

    new_user = User(
        name=user_in.name,
        email=norm_email,
        password_hash=hashed_pw,
        role=user_in.role,
        is_active=True,
        is_verified=False,
        email_verified=False,
        email_verified_at=None,
        email_verification_token_hash=token_hash,
        email_verification_expires_at=expires_at,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    frontend_base = settings.FRONTEND_URL.rstrip("/")
    verification_url = f"{frontend_base}/verify-email?token={raw_token}"
    try:
        sent = send_verification_email(
            to_email=new_user.email,
            name=new_user.name,
            verification_url=verification_url,
        )
        if not sent:
            raise RuntimeError("Email provider dispatch returned failure.")
    except Exception as exc:
        logger.error("Failed to dispatch verification email to %s: %s", new_user.email, type(exc).__name__)
        db.delete(new_user)
        db.commit()
        clean_err = str(exc)
        if "token=" in clean_err:
            clean_err = "Email dispatch failed."
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"We couldn't send the verification email. {clean_err}",
        )

    return new_user


def authenticate_user(db: Session, credentials: UserLogin) -> User:
    """Validate user credentials and return the user model."""
    norm_email = credentials.email.strip().lower()
    user = db.query(User).filter(User.email == norm_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        reason = user.deactivated_reason or "Account has been deactivated. Please contact support."
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is deactivated. Reason: {reason}",
        )

    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in. (EMAIL_NOT_VERIFIED)",
        )

    return user


def login_user(db: Session, credentials: UserLogin) -> Token:
    """Authenticate credentials and generate a signed access token."""
    user = authenticate_user(db, credentials)
    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"email": user.email, "role": user.role.value},
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


def verify_email_token(db: Session, token: str) -> dict:
    """Verify cryptographically secure single-use email verification token."""
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token is required.",
        )

    token_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()

    user = (
        db.query(User)
        .filter(User.email_verification_token_hash == token_hash)
        .with_for_update()
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used verification link.",
        )

    now = datetime.now(timezone.utc)

    # If the user is already verified, return successful response immediately
    if user.email_verified:
        return {"message": "Email is already verified. You can log in.", "email_verified": True}

    if user.email_verification_expires_at and user.email_verification_expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link has expired. Please request a new verification link.",
        )

    user.email_verified = True
    user.email_verified_at = now
    db.commit()
    db.refresh(user)

    return {"message": "Email verified successfully.", "email_verified": True}


def resend_verification_email(db: Session, email: str) -> dict:
    """Rotate verification token and send a fresh verification email with rate-limit cooldown."""
    norm_email = email.strip().lower()
    user = (
        db.query(User)
        .filter(User.email == norm_email)
        .with_for_update()
        .first()
    )

    generic_success = {
        "message": "If an unverified account exists for this email, a verification link has been sent."
    }

    if not user:
        # Prevent email enumeration: return generic success even if user does not exist
        return generic_success

    if user.email_verified:
        # Already verified: return generic success without dispatching new token
        return generic_success

    now = datetime.now(timezone.utc)
    # Check rate limit cooldown
    if user.email_verification_expires_at:
        issued_at = user.email_verification_expires_at - timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)
        elapsed = (now - issued_at).total_seconds()
        if elapsed < settings.EMAIL_RESEND_COOLDOWN_SECONDS:
            cooldown_left = int(settings.EMAIL_RESEND_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {cooldown_left} seconds before requesting another verification email.",
            )

    # Token rotation: invalidate previous token and generate new one
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = now + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)

    user.email_verification_token_hash = token_hash
    user.email_verification_expires_at = expires_at
    db.commit()
    db.refresh(user)

    frontend_base = settings.FRONTEND_URL.rstrip("/")
    verification_url = f"{frontend_base}/verify-email?token={raw_token}"
    try:
        sent = send_verification_email(
            to_email=user.email,
            name=user.name,
            verification_url=verification_url,
        )
        if not sent:
            raise RuntimeError("Email provider dispatch returned failure.")
    except Exception as exc:
        logger.error("Failed to resend verification email to %s: %s", user.email, type(exc).__name__)
        clean_err = str(exc)
        if "token=" in clean_err:
            clean_err = "Email dispatch failed."
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"We couldn't send the verification email. {clean_err}",
        )

    return generic_success


def authenticate_google_user(db: Session, token_str: str) -> Token:
    """Verify Google ID token, find or register user, and return JWT token."""
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests

    if not token_str or not token_str.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google ID token is required.",
        )

    try:
        req = google_requests.Request()
        id_info = google_id_token.verify_oauth2_token(
            token_str.strip(),
            req,
            clock_skew_in_seconds=60,
        )
    except Exception as exc:
        logger.warning("Google ID token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google authentication failed: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if id_info.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token issuer.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate token audience / authorized party against known client IDs
    expected_cids = {
        cid.strip()
        for cid in [
            settings.GOOGLE_CLIENT_ID,
            "161378154091-a5q3ifr8k9j5a8u4v81namd2v6ff4ocv.apps.googleusercontent.com",
        ]
        if cid and cid.strip()
    }
    if expected_cids:
        token_aud = id_info.get("aud")
        token_azp = id_info.get("azp")
        aud_list = [token_aud] if isinstance(token_aud, str) else (token_aud if isinstance(token_aud, list) else [])
        matches = any(a in expected_cids for a in aud_list) or (token_azp in expected_cids)
        if not matches:
            logger.warning("Google token audience mismatch: aud=%s azp=%s expected=%s", token_aud, token_azp, expected_cids)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google token was not issued for this application.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    google_sub = id_info.get("sub")
    if not google_sub or not str(google_sub).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token payload does not contain a subject identifier (sub).",
        )
    google_sub = str(google_sub).strip()

    email = id_info.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token payload does not contain an email address.",
        )

    if not id_info.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account email is not verified.",
        )

    norm_email = email.strip().lower()
    name = (id_info.get("name") or norm_email.split("@")[0]).strip()
    now = datetime.now(timezone.utc)

    # 1. Primary lookup by stable Google sub identifier
    user = db.query(User).filter(User.google_id == google_sub).first()

    # 2. Secondary lookup by email for account linking
    if not user:
        user = db.query(User).filter(User.email == norm_email).first()
        if user:
            # Safely link Google identity to existing account, preserving profile, connections, reputation
            user.google_id = google_sub
            if not user.email_verified:
                user.email_verified = True
                user.email_verified_at = now
            db.commit()
            db.refresh(user)
        else:
            # 3. Create new account with Google ID
            random_pw = secrets.token_urlsafe(32)
            hashed_pw = hash_password(random_pw)
            user = User(
                name=name,
                email=norm_email,
                google_id=google_sub,
                password_hash=hashed_pw,
                role=UserRole.NEWCOMER,
                is_active=True,
                is_verified=True,
                email_verified=True,
                email_verified_at=now,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    if not user.is_active:
        reason = user.deactivated_reason or "Account has been deactivated. Please contact support."
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is deactivated. Reason: {reason}",
        )

    if not user.email_verified:
        user.email_verified = True
        user.email_verified_at = now
        db.commit()
        db.refresh(user)

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={"email": user.email, "role": user.role.value},
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )
