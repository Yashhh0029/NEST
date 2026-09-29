"""API routers package."""

from app.api.auth import router as auth_router
from app.api.embeddings import router as embeddings_router
from app.api.profile import router as profile_router
from app.api.requests import router as requests_router

__all__ = ["auth_router", "embeddings_router", "profile_router", "requests_router"]
