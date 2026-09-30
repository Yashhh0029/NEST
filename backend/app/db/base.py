"""Import all models for Alembic auto-discovery."""

from app.db.database import Base
from app.models.availability import (
    HelperAvailabilityException,
    HelperAvailabilitySlot,
)
from app.models.community import (
    CommunityAnswer,
    CommunityAnswerVote,
    CommunityQuestion,
)
from app.models.connection import Connection, ConnectionStatus
from app.models.conversation import Conversation, Message
from app.models.embedding import Embedding
from app.models.location import Location
from app.models.profile import Profile
from app.models.request import Request, RequestSavedResource
from app.models.request_location import RequestLocation
from app.models.review import Review
from app.models.safety import Block, ModerationAction, Report
from app.models.session import AssistanceSession
from app.models.skill import Skill, UserSkill
from app.models.user import User, UserRole

__all__ = [
    "AssistanceSession",
    "Base",
    "Block",
    "CommunityAnswer",
    "CommunityAnswerVote",
    "CommunityQuestion",
    "Connection",
    "ConnectionStatus",
    "Conversation",
    "Embedding",
    "HelperAvailabilityException",
    "HelperAvailabilitySlot",
    "Location",
    "Message",
    "ModerationAction",
    "Profile",
    "Report",
    "Request",
    "RequestLocation",
    "RequestSavedResource",
    "Review",
    "Skill",
    "User",
    "UserRole",
    "UserSkill",
]
