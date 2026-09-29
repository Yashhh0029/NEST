import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SkillCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Skill or expertise name")
    proficiency: Optional[str] = Field(None, max_length=50, description="Optional proficiency level")
    years_experience: Optional[float] = Field(None, ge=0.0, le=70.0, description="Years of experience with this skill")

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Skill name cannot be empty or blank")
        return cleaned

    @field_validator("proficiency")
    @classmethod
    def clean_proficiency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip().lower()
            return cleaned if cleaned else None
        return v


class SkillResponse(BaseModel):
    id: uuid.UUID
    name: str
    normalized_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserSkillResponse(BaseModel):
    id: uuid.UUID
    skill_id: uuid.UUID
    skill_name: str
    proficiency: Optional[str] = None
    years_experience: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
