"""Import all models for Alembic auto-discovery."""

from app.db.database import Base
from app.models.embedding import Embedding
from app.models.location import Location
from app.models.profile import Profile
from app.models.request import Request
from app.models.skill import Skill, UserSkill
from app.models.user import User, UserRole

__all__ = [
    "Base",
    "Embedding",
    "Location",
    "Profile",
    "Request",
    "Skill",
    "User",
    "UserRole",
    "UserSkill",
]
