from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.connections import router as connections_router
from app.api.embeddings import router as embeddings_router
from app.api.location import router as location_router
from app.api.matching import router as matching_router
from app.api.profile import router as profile_router
from app.api.requests import router as requests_router
from app.api.reviews import router as reviews_router
from app.api.ws_chat import router as ws_router
from app.core.config import settings
from app.db.database import get_db

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="NEST — AI-Powered Community Matching Platform. Find Your People. Find Your Place.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS
origins = [origin.strip() for origin in settings.BACKEND_CORS_ORIGINS if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(profile_router, prefix=settings.API_V1_STR)
app.include_router(requests_router, prefix=settings.API_V1_STR)
app.include_router(embeddings_router, prefix=settings.API_V1_STR)
app.include_router(matching_router, prefix=f"{settings.API_V1_STR}/matching")
app.include_router(location_router, prefix=f"{settings.API_V1_STR}/location", tags=["Location & Google Maps"])
app.include_router(connections_router, prefix=f"{settings.API_V1_STR}/connections")
app.include_router(chat_router, prefix=settings.API_V1_STR)
app.include_router(reviews_router, prefix=settings.API_V1_STR)
app.include_router(ws_router)


@app.get("/", tags=["Root"])
def root():
    """Root endpoint providing platform discovery metadata."""
    return {
        "name": settings.PROJECT_NAME,
        "tagline": "Find Your People. Find Your Place.",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "operational",
    }


@app.get(
    "/api/health",
    tags=["System"],
    summary="Health check with PostgreSQL verification",
)
def health_check(db: Session = Depends(get_db)):
    """
    Real health endpoint verifying application runtime and PostgreSQL connectivity.
    Never returns false 'connected' if database is unreachable.
    """
    db_status = "disconnected"
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:
        db_status = f"error: {str(exc)}"

    is_healthy = db_status == "connected"
    return {
        "status": "ok" if is_healthy else "degraded",
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "api": "online",
    }
