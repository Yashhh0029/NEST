import uuid
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.skill import Skill, UserSkill
from app.models.user import User
from app.schemas.skill import SkillCreate, UserSkillResponse


def normalize_skill_name(name: str) -> str:
    """Normalize skill name by trimming and converting internal whitespace to single spaces and lowercase."""
    return " ".join(name.strip().lower().split())


def add_user_skill(db: Session, user: User, skill_in: SkillCreate) -> UserSkillResponse:
    """
    Add a skill to user's profile.
    Reuses existing normalized Skill record or creates a new one.
    Rejects duplicate skill additions for the same user.
    """
    clean_name = " ".join(skill_in.name.strip().split())
    normalized = normalize_skill_name(clean_name)

    # 1. Find or create master Skill
    skill = db.query(Skill).filter(Skill.normalized_name == normalized).first()
    if not skill:
        skill = Skill(name=clean_name, normalized_name=normalized)
        db.add(skill)
        db.flush()

    # 2. Prevent duplicate user_skills
    existing_link = (
        db.query(UserSkill)
        .filter(UserSkill.user_id == user.id, UserSkill.skill_id == skill.id)
        .first()
    )
    if existing_link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Skill '{skill.name}' is already added to your profile.",
        )

    # 3. Create UserSkill link
    user_skill = UserSkill(
        user_id=user.id,
        skill_id=skill.id,
        proficiency=skill_in.proficiency,
        years_experience=skill_in.years_experience,
    )
    db.add(user_skill)
    db.commit()
    db.refresh(user_skill)

    return UserSkillResponse(
        id=user_skill.id,
        skill_id=skill.id,
        skill_name=skill.name,
        proficiency=user_skill.proficiency,
        years_experience=user_skill.years_experience,
        created_at=user_skill.created_at,
    )


def get_user_skills(db: Session, user: User) -> List[UserSkillResponse]:
    """Retrieve all skills associated with the user."""
    results = (
        db.query(UserSkill, Skill.name)
        .join(Skill, UserSkill.skill_id == Skill.id)
        .filter(UserSkill.user_id == user.id)
        .order_by(Skill.name.asc())
        .all()
    )
    return [
        UserSkillResponse(
            id=us.id,
            skill_id=us.skill_id,
            skill_name=name,
            proficiency=us.proficiency,
            years_experience=us.years_experience,
            created_at=us.created_at,
        )
        for us, name in results
    ]


def remove_user_skill(db: Session, user: User, skill_id: uuid.UUID) -> bool:
    """
    Remove a skill from the user's profile.
    Can be referenced either by skill_id or user_skill.id.
    """
    user_skill = (
        db.query(UserSkill)
        .filter(
            UserSkill.user_id == user.id,
            (UserSkill.skill_id == skill_id) | (UserSkill.id == skill_id),
        )
        .first()
    )
    if not user_skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found in your profile.",
        )

    db.delete(user_skill)
    db.commit()
    return True
