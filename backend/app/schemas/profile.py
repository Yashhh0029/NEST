import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.auth import UserResponse
from app.schemas.location import LocationResponse
from app.schemas.skill import UserSkillResponse


class ProfileBase(BaseModel):
    headline: Optional[str] = Field(None, max_length=255, description="Short professional or personal headline")
    bio: Optional[str] = Field(None, description="Detailed user biography")
    occupation: Optional[str] = Field(None, max_length=255, description="Current occupation or profession")
    organization: Optional[str] = Field(None, max_length=255, description="Company or college")
    years_experience: Optional[float] = Field(default=0.0, ge=0.0, le=70.0, description="Total years in area/industry")
    languages: Optional[List[str]] = Field(default_factory=list, description="Spoken languages")
    help_description: Optional[str] = Field(
        None,
        description="Natural-language description of what local advice or help this user can provide",
    )
    needs_description: Optional[str] = Field(
        None,
        description="Natural-language description of what newcomer assistance this user requires",
    )
    availability: Optional[bool] = Field(default=True, description="Whether currently accepting new connections")


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    pass


class ProfilePatch(BaseModel):
    headline: Optional[str] = None
    bio: Optional[str] = None
    occupation: Optional[str] = None
    organization: Optional[str] = None
    years_experience: Optional[float] = Field(None, ge=0.0, le=70.0)
    languages: Optional[List[str]] = None
    help_description: Optional[str] = None
    needs_description: Optional[str] = None
    availability: Optional[bool] = None


class ProfileResponse(ProfileBase):
    id: uuid.UUID
    user_id: uuid.UUID
    availability: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FullProfileResponse(BaseModel):
    user: UserResponse
    profile: Optional[ProfileResponse] = None
    location: Optional[LocationResponse] = None
    skills: List[UserSkillResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PublicUserSummary(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicLocationSummary(BaseModel):
    city: Optional[str] = None
    area: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PublicProfileResponse(BaseModel):
    user: PublicUserSummary
    profile: Optional[ProfileResponse] = None
    location: Optional[PublicLocationSummary] = None
    skills: List[UserSkillResponse] = Field(default_factory=list)
    reputation: Optional[dict] = None
    public_availability: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)
