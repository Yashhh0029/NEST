from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import (
    GoogleAuthRequest,
    ResendVerificationRequest,
    ResendVerificationResponse,
    Token,
    UserLogin,
    UserRegister,
    UserResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.services.auth_service import (
    authenticate_google_user,
    login_user,
    register_user,
    resend_verification_email,
    verify_email_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a newcomer, helper, or multi-role user with securely hashed credentials and sends verification email.",
)
def register(
    user_in: UserRegister,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Register a new user account."""
    user = register_user(db, user_in)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and obtain JWT token",
    description="Validates credentials and verified status, returning signed JWT access token and user profile.",
)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),
) -> Token:
    """Authenticate user credentials and issue JWT."""
    return login_user(db, credentials)


@router.get(
    "/verify-email",
    response_model=VerifyEmailResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify email using query token",
    description="Verifies a single-use token provided in email verification link and marks account active.",
)
def verify_email_get(
    token: str = Query(..., description="Single-use email verification token"),
    db: Session = Depends(get_db),
) -> VerifyEmailResponse:
    """Verify email via query parameter token."""
    res = verify_email_token(db, token)
    return VerifyEmailResponse(**res)


@router.post(
    "/verify-email",
    response_model=VerifyEmailResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify email using JSON body token",
    description="Verifies a single-use token sent in request body from frontend verification page.",
)
def verify_email_post(
    payload: VerifyEmailRequest,
    db: Session = Depends(get_db),
) -> VerifyEmailResponse:
    """Verify email via POST body token."""
    res = verify_email_token(db, payload.token)
    return VerifyEmailResponse(**res)


@router.post(
    "/resend-verification",
    response_model=ResendVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Resend verification email",
    description="Rotates verification token and re-sends verification email with rate-limit protection.",
)
def resend_verification(
    payload: ResendVerificationRequest,
    db: Session = Depends(get_db),
) -> ResendVerificationResponse:
    """Resend email verification link."""
    res = resend_verification_email(db, payload.email)
    return ResendVerificationResponse(**res)


@router.post(
    "/google",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Authenticate or register user via Google OAuth ID token",
    description="Verifies Google ID token from Google Identity Services, creates user if absent, and returns JWT session token.",
)
def google_auth(
    payload: GoogleAuthRequest,
    db: Session = Depends(get_db),
) -> Token:
    """Authenticate with Google ID token."""
    token_str = payload.id_token or payload.credential or ""
    return authenticate_google_user(db, token_str)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
    description="Returns authenticated user details extracted from verified JWT bearer token.",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return profile of currently logged-in user."""
    return UserResponse.model_validate(current_user)
