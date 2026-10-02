from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.models.location import Location
from app.models.profile import Profile
from app.models.skill import Skill, UserSkill
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.location import LocationCreate, LocationResponse
from app.schemas.profile import (
    FullProfileResponse,
    ProfileCreate,
    ProfilePatch,
    ProfileResponse,
    ProfileUpdate,
)
from app.schemas.skill import UserSkillResponse


def get_full_profile(db: Session, user: User) -> FullProfileResponse:
    """Retrieve combined user identity, profile, primary location, and skills."""
    # 1. Profile
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    profile_resp = ProfileResponse.model_validate(profile) if profile else None

    # 2. Location
    location = (
        db.query(Location)
        .filter(Location.user_id == user.id, Location.location_label == "Primary")
        .first()
    )
    location_resp = LocationResponse.model_validate(location) if location else None

    # 3. User Skills with Skill names
    user_skills_raw = (
        db.query(UserSkill, Skill.name)
        .join(Skill, UserSkill.skill_id == Skill.id)
        .filter(UserSkill.user_id == user.id)
        .order_by(Skill.name.asc())
        .all()
    )

    skills_resp = [
        UserSkillResponse(
            id=us.id,
            skill_id=us.skill_id,
            skill_name=skill_name,
            proficiency=us.proficiency,
            years_experience=us.years_experience,
            created_at=us.created_at,
        )
        for us, skill_name in user_skills_raw
    ]

    return FullProfileResponse(
        user=UserResponse.model_validate(user),
        profile=profile_resp,
        location=location_resp,
        skills=skills_resp,
    )


def upsert_profile(db: Session, user: User, profile_in: ProfileUpdate) -> Profile:
    """Create profile if it doesn't exist, or completely update existing profile."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    now = datetime.now(timezone.utc)

    if not profile:
        profile = Profile(
            user_id=user.id,
            headline=profile_in.headline,
            bio=profile_in.bio,
            occupation=profile_in.occupation,
            organization=profile_in.organization,
            years_experience=profile_in.years_experience,
            languages=profile_in.languages or [],
            help_description=profile_in.help_description,
            needs_description=profile_in.needs_description,
            availability=profile_in.availability if profile_in.availability is not None else True,
            created_at=now,
            updated_at=now,
        )
        db.add(profile)
    else:
        profile.headline = profile_in.headline
        profile.bio = profile_in.bio
        profile.occupation = profile_in.occupation
        profile.organization = profile_in.organization
        profile.years_experience = profile_in.years_experience
        profile.languages = profile_in.languages or []
        profile.help_description = profile_in.help_description
        profile.needs_description = profile_in.needs_description
        if profile_in.availability is not None:
            profile.availability = profile_in.availability
        profile.updated_at = now

    db.commit()
    db.refresh(profile)
    return profile


def patch_profile(db: Session, user: User, patch_in: ProfilePatch) -> Profile:
    """Partially update an existing profile or create one with provided fields."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    now = datetime.now(timezone.utc)

    if not profile:
        profile = Profile(
            user_id=user.id,
            headline=patch_in.headline,
            bio=patch_in.bio,
            occupation=patch_in.occupation,
            organization=patch_in.organization,
            years_experience=patch_in.years_experience or 0.0,
            languages=patch_in.languages or [],
            help_description=patch_in.help_description,
            needs_description=patch_in.needs_description,
            availability=patch_in.availability if patch_in.availability is not None else True,
            created_at=now,
            updated_at=now,
        )
        db.add(profile)
    else:
        update_data = patch_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
        profile.updated_at = now

    db.commit()
    db.refresh(profile)
    return profile


def upsert_user_location(db: Session, user: User, loc_in: LocationCreate) -> Location:
    """Set or update user's location (defaults to Primary label)."""
    label = loc_in.location_label or "Primary"
    loc = (
        db.query(Location)
        .filter(Location.user_id == user.id, Location.location_label == label)
        .first()
    )
    now = datetime.now(timezone.utc)

    if not loc:
        loc = Location(
            user_id=user.id,
            city=loc_in.city,
            area=loc_in.area,
            state=loc_in.state,
            country=loc_in.country or "India",
            latitude=loc_in.latitude,
            longitude=loc_in.longitude,
            location_label=label,
            display_name=loc_in.display_name,
            place_types=loc_in.place_types,
            google_place_id=loc_in.google_place_id,
            formatted_address=loc_in.formatted_address,
            postal_code=loc_in.postal_code,
            location_source=loc_in.location_source or "manual",
            location_precision=loc_in.location_precision or "locality",
            created_at=now,
            updated_at=now,
        )
        db.add(loc)
    else:
        loc.city = loc_in.city
        loc.area = loc_in.area
        loc.state = loc_in.state
        loc.country = loc_in.country or "India"
        loc.latitude = loc_in.latitude
        loc.longitude = loc_in.longitude
        loc.display_name = loc_in.display_name
        loc.place_types = loc_in.place_types
        loc.google_place_id = loc_in.google_place_id
        loc.formatted_address = loc_in.formatted_address
        loc.postal_code = loc_in.postal_code
        if loc_in.location_source:
            loc.location_source = loc_in.location_source
        if loc_in.location_precision:
            loc.location_precision = loc_in.location_precision
        loc.updated_at = now

    db.commit()
    db.refresh(loc)
    return loc


def get_user_location(
    db: Session, user: User, location_label: str = "Primary"
) -> Optional[Location]:
    """Get location by user and label."""
    return (
        db.query(Location)
        .filter(Location.user_id == user.id, Location.location_label == location_label)
        .first()
    )


def delete_user_location(
    db: Session, user: User, location_label: str = "Primary"
) -> bool:
    """Delete a user's location by label."""
    loc = (
        db.query(Location)
        .filter(Location.user_id == user.id, Location.location_label == location_label)
        .first()
    )
    if not loc:
        return False
    db.delete(loc)
    db.commit()
    return True


def get_public_profile(
    db: Session,
    target_user_id: "uuid.UUID",
    caller: Optional[User] = None,
):
    """
    Retrieve public-safe profile for a user.
    Excludes exact coordinates, phone numbers, and emails.
    Includes verified reputation and coarse availability.
    """
    import uuid
    from fastapi import HTTPException, status
    from app.models.safety import Block
    from app.schemas.profile import (
        ProfileResponse,
        PublicLocationSummary,
        PublicProfileResponse,
        PublicUserSummary,
    )
    from app.schemas.skill import UserSkillResponse
    from app.services.availability_service import get_public_or_detailed_availability
    from app.services.review_service import get_user_reputation

    target_user = db.query(User).filter(User.id == target_user_id, User.is_active == True).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or inactive.",
        )

    if caller and caller.id != target_user.id:
        blocked = (
            db.query(Block)
            .filter(
                ((Block.blocker_id == caller.id) & (Block.blocked_id == target_user.id))
                | ((Block.blocker_id == target_user.id) & (Block.blocked_id == caller.id))
            )
            .first()
        )
        if blocked:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

    profile = db.query(Profile).filter(Profile.user_id == target_user.id).first()
    profile_resp = ProfileResponse.model_validate(profile) if profile else None

    loc = (
        db.query(Location)
        .filter(Location.user_id == target_user.id, Location.location_label == "Primary")
        .first()
    )
    if not loc:
        loc = db.query(Location).filter(Location.user_id == target_user.id).first()

    loc_summary = (
        PublicLocationSummary(
            city=loc.city,
            area=loc.area,
            state=loc.state,
            country=loc.country,
        )
        if loc
        else None
    )

    user_skills_raw = (
        db.query(UserSkill, Skill.name)
        .join(Skill, UserSkill.skill_id == Skill.id)
        .filter(UserSkill.user_id == target_user.id)
        .order_by(Skill.name.asc())
        .all()
    )
    skills_resp = [
        UserSkillResponse(
            id=us.id,
            skill_id=us.skill_id,
            skill_name=skill_name,
            proficiency=us.proficiency,
            years_experience=us.years_experience,
            created_at=us.created_at,
        )
        for us, skill_name in user_skills_raw
    ]

    rep = get_user_reputation(db, target_user.id).model_dump()
    avail = get_public_or_detailed_availability(db, target_user.id, viewer=caller).model_dump()

    return PublicProfileResponse(
        user=PublicUserSummary.model_validate(target_user),
        profile=profile_resp,
        location=loc_summary,
        skills=skills_resp,
        reputation=rep,
        public_availability=avail,
    )
