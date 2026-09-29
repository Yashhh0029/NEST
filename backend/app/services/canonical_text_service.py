import hashlib
from typing import List, Optional
from app.models.location import Location
from app.models.profile import Profile
from app.models.request import Request
from app.models.user import User


def compute_source_hash(text: str) -> str:
    """Calculate deterministic SHA-256 hash of normalized text."""
    normalized = " ".join(text.strip().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_profile_canonical_text(
    profile: Optional[Profile],
    user: User,
    location: Optional[Location] = None,
    skills: Optional[List[str]] = None,
) -> str:
    """
    Construct standardized, dense canonical text representing a user profile
    for semantic embedding generation.
    """
    parts: List[str] = []

    # Identity & Professional Headline
    parts.append(f"Name: {user.name}. Role: {user.role.value}.")
    if profile:
        if profile.headline:
            parts.append(f"Headline: {profile.headline.strip()}.")
        if profile.occupation:
            org_str = f" at {profile.organization.strip()}" if profile.organization else ""
            parts.append(f"Occupation: {profile.occupation.strip()}{org_str}.")
        if profile.years_experience and profile.years_experience > 0:
            parts.append(f"Experience: {profile.years_experience:g} years.")
        if profile.bio:
            parts.append(f"Bio: {profile.bio.strip()}.")

    # Location Context
    if location:
        loc_parts = []
        if location.area:
            loc_parts.append(location.area.strip())
        if location.city:
            loc_parts.append(location.city.strip())
        if location.state:
            loc_parts.append(location.state.strip())
        if loc_parts:
            parts.append(f"Location: {', '.join(loc_parts)}.")

    # Core AI Help & Needs Descriptions
    if profile:
        if profile.help_description:
            parts.append(f"Can Help With: {profile.help_description.strip()}.")
        if profile.needs_description:
            parts.append(f"Needs Help With: {profile.needs_description.strip()}.")
        if profile.languages and len(profile.languages) > 0:
            parts.append(f"Languages: {', '.join(profile.languages)}.")

    # Skills & Expertise
    if skills and len(skills) > 0:
        parts.append(f"Skills: {', '.join(skills)}.")

    return "\n".join(parts)


def build_request_canonical_text(request: Request) -> str:
    """
    Construct standardized canonical text representing a newcomer request
    combining raw query and structured extracted requirements for semantic search.
    """
    parts: List[str] = [f"Request: {request.raw_text.strip()}."]

    req_meta = request.extracted_requirements or {}
    needs_meta = req_meta.get("needs", [])
    if needs_meta:
        need_items = [f"{n.get('category')}: {n.get('item')}" for n in needs_meta if isinstance(n, dict)]
        if need_items:
            parts.append(f"Needs: {', '.join(need_items)}.")

    if request.preferences and len(request.preferences) > 0:
        parts.append(f"Preferences: {', '.join(request.preferences)}.")

    loc_parts = []
    if request.area:
        loc_parts.append(request.area.strip())
    if request.city:
        loc_parts.append(request.city.strip())
    if loc_parts:
        parts.append(f"Target Location: {', '.join(loc_parts)}.")

    if request.budget_amount:
        op_str = f"{request.budget_operator} " if request.budget_operator else ""
        period_str = f" {request.budget_period}" if request.budget_period else ""
        parts.append(f"Budget: {op_str}{request.budget_currency or 'INR'} {request.budget_amount:g}{period_str}.")

    if request.user_context and len(request.user_context) > 0:
        parts.append(f"Context: {', '.join(request.user_context)}.")

    return "\n".join(parts)
