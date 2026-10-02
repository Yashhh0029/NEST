import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Response, status
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
from app.api.resources import router as resources_router
from app.api.reviews import router as reviews_router
from app.api.safety import router as safety_router
from app.api.community import router as community_router
from app.api.intelligence import router as intelligence_router
from app.api.availability import router as availability_router
from app.api.sessions import router as sessions_router
from app.api.ws_chat import router as ws_router
from app.core.config import settings
from app.db.database import get_db, engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Production-grade application lifespan manager.
    Handles startup checks and graceful cleanup on termination.
    """
    logger.info(f"Starting {settings.PROJECT_NAME} in [{settings.ENVIRONMENT}] mode.")
    try:
        # Pre-verify database connection on startup
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successfully established.")
    except Exception as exc:
        logger.warning(f"Database pre-flight check warning (will retry on requests): {exc}")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}. Disposing connection pools...")
    engine.dispose()
    logger.info("Shutdown complete.")


docs_enabled = settings.ENABLE_DOCS

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="NEST — AI-Powered Community Matching Platform. Find Your People. Find Your Place.",
    version="1.0.0",
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
    lifespan=lifespan,
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
app.include_router(resources_router, prefix=settings.API_V1_STR)
app.include_router(safety_router, prefix=settings.API_V1_STR)
app.include_router(community_router, prefix=settings.API_V1_STR)
app.include_router(intelligence_router, prefix=settings.API_V1_STR)
app.include_router(availability_router, prefix=settings.API_V1_STR)
app.include_router(sessions_router, prefix=settings.API_V1_STR)
app.include_router(ws_router)


@app.get("/", tags=["Root"])
def root():
    """Root endpoint providing platform discovery metadata."""
    return {
        "name": settings.PROJECT_NAME,
        "tagline": "Find Your People. Find Your Place.",
        "version": "1.0.0",
        "docs": "/docs" if docs_enabled else None,
        "status": "operational",
    }


def _execute_health_check(response: Response, db: Session):
    db_status = "disconnected"
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:
        db_status = f"error: {str(exc)}"

    is_healthy = db_status == "connected"
    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if is_healthy else "degraded",
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "api": "online",
    }


@app.get(
    "/api/health",
    tags=["System"],
    summary="Health check with PostgreSQL verification",
)
def api_health_check(response: Response, db: Session = Depends(get_db)):
    """
    Standard API health endpoint verifying application runtime and PostgreSQL connectivity.
    Returns HTTP 200 on success, HTTP 503 on database disconnect.
    """
    return _execute_health_check(response, db)


@app.get(
    "/health",
    tags=["System"],
    summary="Root health check for cloud load balancers and orchestrators",
)
def root_health_check(response: Response, db: Session = Depends(get_db)):
    """
    Root-level health check endpoint for container orchestrators (Render, AWS, GCP, Fly.io).
    """
    return _execute_health_check(response, db)

