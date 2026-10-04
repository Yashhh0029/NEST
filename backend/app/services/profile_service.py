from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.models.location import Location
from app.models.profile import Profile
from app.models.skill import Skill, UserSkill
from app.models.user import User, UserRole
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
from app.services.google_maps_service import google_maps_service


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

    if profile_in.role is not None and profile_in.role in [UserRole.NEWCOMER, UserRole.HELPER, UserRole.BOTH]:
        user.role = profile_in.role
        db.add(user)

    db.commit()
    db.refresh(profile)
    return profile


def patch_profile(db: Session, user: User, patch_in: ProfilePatch) -> Profile:
    """Partially update an existing profile or create one with provided fields."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    now = datetime.now(timezone.utc)

    if patch_in.role is not None and patch_in.role in [UserRole.NEWCOMER, UserRole.HELPER, UserRole.BOTH]:
        user.role = patch_in.role
        db.add(user)

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
        update_data.pop("role", None)
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

    final_place_id = loc_in.google_place_id
    final_lat = loc_in.latitude
    final_lon = loc_in.longitude
    final_city = loc_in.city
    final_area = loc_in.area
    final_state = loc_in.state
    final_country = loc_in.country or "India"
    final_postal = loc_in.postal_code
    final_display = loc_in.display_name
    final_formatted = loc_in.formatted_address
    final_source = loc_in.location_source or "manual"
    final_precision = loc_in.location_precision or "locality"

    # Canonical source of truth: if Google Place ID is present, fetch authoritative details
    if final_place_id:
        place_details = google_maps_service.get_place_details(final_place_id)
        if place_details:
            if final_lat is None and place_details.latitude is not None:
                final_lat = place_details.latitude
            if final_lon is None and place_details.longitude is not None:
                final_lon = place_details.longitude
            if not final_formatted and place_details.formatted_address:
                final_formatted = place_details.formatted_address
            if not final_city and place_details.city:
                final_city = place_details.city
            if not final_area and place_details.area:
                final_area = place_details.area
            if not final_state and place_details.state:
                final_state = place_details.state
            if not final_postal and place_details.postal_code:
                final_postal = place_details.postal_code
            if not final_display:
                final_display = place_details.display_name or place_details.name
            if place_details.location_source:
                final_source = place_details.location_source
            if place_details.location_precision:
                final_precision = place_details.location_precision

    if not loc:
        loc = Location(
            user_id=user.id,
            city=final_city,
            area=final_area,
            state=final_state,
            country=final_country,
            latitude=final_lat,
            longitude=final_lon,
            location_label=label,
            display_name=final_display,
            place_types=loc_in.place_types,
            google_place_id=final_place_id,
            formatted_address=final_formatted,
            postal_code=final_postal,
            location_source=final_source,
            location_precision=final_precision,
            created_at=now,
            updated_at=now,
        )
        db.add(loc)
    else:
        loc.city = final_city
        loc.area = final_area
        loc.state = final_state
        loc.country = final_country
        loc.latitude = final_lat
        loc.longitude = final_lon
        loc.display_name = final_display
        loc.place_types = loc_in.place_types
        loc.google_place_id = final_place_id
        loc.formatted_address = final_formatted
        loc.postal_code = final_postal
        loc.location_source = final_source
        loc.location_precision = final_precision
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
