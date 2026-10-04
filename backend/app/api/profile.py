import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, get_db, get_optional_current_user
from app.models.user import User, UserRole
from app.schemas.auth import UserResponse
from app.schemas.location import LocationCreate, LocationResponse
from app.schemas.profile import (
    FullProfileResponse,
    ProfilePatch,
    ProfileResponse,
    ProfileUpdate,
    PublicProfileResponse,
    RoleUpdate,
)
from app.schemas.skill import SkillCreate, UserSkillResponse
from app.services.profile_service import (
    delete_user_location,
    get_full_profile,
    get_public_profile,
    get_user_location,
    patch_profile,
    upsert_profile,
    upsert_user_location,
)
from app.services.skill_service import (
    add_user_skill,
    get_user_skills,
    remove_user_skill,
)

router = APIRouter(prefix="/profile", tags=["User Profile & Location"])


# ==========================================
# 1. Profile Core Endpoints
# ==========================================

@router.get(
    "/me",
    response_model=FullProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get complete user profile",
    description="Returns authenticated user details, biography, location, and skills.",
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FullProfileResponse:
    """Return full profile for current user."""
    return get_full_profile(db, current_user)


@router.put(
    "/me",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or completely update user profile",
    description="Upserts the user profile with provided headline, bio, experience, languages, help/needs descriptions, and availability.",
)
def update_my_profile(
    profile_in: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    """Create or update user profile."""
    profile = upsert_profile(db, current_user, profile_in)
    return ProfileResponse.model_validate(profile)


@router.patch(
    "/me",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Partially update user profile",
    description="Updates only the fields provided in the request body.",
)
def patch_my_profile(
    patch_in: ProfilePatch,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    """Partially update user profile."""
    profile = patch_profile(db, current_user, patch_in)
    return ProfileResponse.model_validate(profile)


@router.put(
    "/me/role",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user community role",
    description="Updates user role between newcomer, helper, and both.",
)
def update_my_role(
    role_in: RoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Update current user community role."""
    if role_in.role not in [UserRole.NEWCOMER, UserRole.HELPER, UserRole.BOTH]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be newcomer, helper, or both.",
        )
    current_user.role = role_in.role
    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)


# ==========================================
# 2. Location Endpoints
# ==========================================

@router.put(
    "/me/location",
    response_model=LocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Set or update primary user location",
    description="Sets city, area, state, country, and validated coordinates [-90..90, -180..180].",
)
def set_my_location(
    loc_in: LocationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LocationResponse:
    """Set or update user location."""
    location = upsert_user_location(db, current_user, loc_in)
    return LocationResponse.model_validate(location)


@router.get(
    "/me/location",
    response_model=LocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user primary location",
    description="Returns current primary location for authenticated user.",
)
def get_my_location(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LocationResponse:
    """Get user primary location."""
    location = get_user_location(db, current_user, location_label="Primary")
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not configured for this user.",
        )
    return LocationResponse.model_validate(location)


@router.delete(
    "/me/location",
    status_code=status.HTTP_200_OK,
    summary="Delete primary user location",
    description="Deletes primary location associated with authenticated user.",
)
def delete_my_location(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete user primary location."""
    deleted = delete_user_location(db, current_user, location_label="Primary")
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found.",
        )
    return {"detail": "Location deleted successfully"}


# ==========================================
# 3. Skills Endpoints
# ==========================================

@router.post(
    "/me/skills",
    response_model=UserSkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a skill or expertise to user profile",
    description="Normalizes skill name, prevents duplicates, and associates skill with user profile.",
)
def add_my_skill(
    skill_in: SkillCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserSkillResponse:
    """Add a skill to authenticated user's profile."""
    return add_user_skill(db, current_user, skill_in)


@router.get(
    "/me/skills",
    response_model=List[UserSkillResponse],
    status_code=status.HTTP_200_OK,
    summary="List all skills for user profile",
    description="Returns list of expertise categories and skills linked to this user.",
)
def get_my_skills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[UserSkillResponse]:
    """Get all skills for authenticated user."""
    return get_user_skills(db, current_user)


@router.delete(
    "/me/skills/{skill_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a skill from user profile",
    description="Unlinks skill from authenticated user profile.",
)
def delete_my_skill(
    skill_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a skill from authenticated user's profile."""
    remove_user_skill(db, current_user, skill_id)
    return {"detail": "Skill removed successfully"}


@router.get(
    "/users/{user_id}",
    response_model=PublicProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get public helper profile",
    description="Returns public-safe profile, skills, reputation, and availability without exposing private details.",
)
def get_user_public_profile(
    user_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> PublicProfileResponse:
    """Return public profile of a user."""
    return get_public_profile(db, user_id, caller=current_user)
