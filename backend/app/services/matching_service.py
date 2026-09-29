from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Tuple
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.embedding import Embedding
from app.models.location import Location
from app.models.profile import Profile
from app.models.request import Request
from app.models.request_location import RequestLocation
from app.models.skill import Skill, UserSkill
from app.models.user import User
from app.schemas.matching import (
    DimensionStatusEnum,
    DimensionStatuses,
    HelperCandidate,
    MatchingResponse,
    MatchReason,
    MatchScores,
    MatchWeightsInput,
    TargetLocationSummary,
    WeightsSummary,
)
from app.services.embedding_repository import (
    sync_user_profile_embedding,
    sync_user_request_embedding,
)
from app.services.google_maps_service import google_maps_service


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on the Earth in kilometers."""
    r = 6371.0  # Earth's mean radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return r * c


def calculate_location_score(
    req_lat: Optional[float],
    req_lon: Optional[float],
    cand_lat: Optional[float],
    cand_lon: Optional[float],
    req_city: Optional[str],
    req_area: Optional[str],
    cand_city: Optional[str],
    cand_area: Optional[str],
) -> Tuple[float, Optional[float]]:
    """
    Compute location compatibility score in [0.0, 1.0] and distance in km.
    Uses real GPS coordinates with smooth exponential decay when available,
    falling back to city/area text matching.
    """
    if (
        req_lat is not None
        and req_lon is not None
        and cand_lat is not None
        and cand_lon is not None
    ):
        dist_km = haversine_km(req_lat, req_lon, cand_lat, cand_lon)
        # Exponential decay: 0km -> 1.0, 5km -> 0.72, 10km -> 0.51, 25km -> 0.19, 50km -> 0.035
        score = math.exp(-dist_km / 15.0)
        return max(0.0, min(1.0, score)), round(dist_km, 1)

    # Fallback to city and area textual hierarchy
    if req_city and cand_city:
        same_city = req_city.strip().lower() == cand_city.strip().lower()
        if same_city:
            if req_area and cand_area and req_area.strip().lower() == cand_area.strip().lower():
                return 0.90, None
            return 0.50, None
        return 0.05, None

    return 0.0, None


def calculate_experience_score(
    profile: Optional[Profile],
    skills_data: List[Tuple[str, Optional[str], Optional[float]]],
    request_keywords: List[str],
) -> float:
    """
    Calculate experience compatibility in [0.0, 1.0] from profile tenure and skills.
    Tenure factor: years_experience / 5.0 (capped at 1.0, min 0.05).
    Skill factor: proficiency weighting for skills relevant to request needs.
    """
    years = profile.years_experience if profile and profile.years_experience else 0.0
    tenure_score = max(0.05, min(1.0, years / 5.0))

    if not skills_data:
        return tenure_score

    # Check for skill relevance against request keywords
    relevant_proficiencies = []
    proficiency_weights = {
        "expert": 1.0,
        "advanced": 0.9,
        "intermediate": 0.7,
        "beginner": 0.4,
    }

    kw_set = {k.lower() for k in request_keywords if k}

    matched_count = 0
    for name, proficiency, _ in skills_data:
        norm_name = name.lower()
        # Direct match or substring match against request keywords
        is_relevant = any(kw in norm_name or norm_name in kw for kw in kw_set)
        if is_relevant:
            matched_count += 1
            weight = proficiency_weights.get((proficiency or "").lower(), 0.6)
            relevant_proficiencies.append(weight)

    if relevant_proficiencies:
        avg_skill_score = sum(relevant_proficiencies) / len(relevant_proficiencies)
        return max(0.0, min(1.0, 0.4 * tenure_score + 0.6 * avg_skill_score))

    return tenure_score


def generate_match_reasons(
    semantic_score: float,
    location_score: float,
    experience_score: float,
    distance_km: Optional[float],
    candidate_city: Optional[str],
    candidate_area: Optional[str],
    years_experience: float,
    skills: List[str],
) -> List[MatchReason]:
    """Generate human-readable explanations based on actual scoring factors."""
    reasons: List[MatchReason] = []

    # 1. Semantic Reason
    sem_pct = int(round(semantic_score * 100))
    if sem_pct >= 70:
        reasons.append(
            MatchReason(
                category="semantic",
                title="Strong Need Alignment",
                explanation=f"Profile and background match your request needs with {sem_pct}% AI semantic similarity.",
            )
        )
    elif sem_pct >= 40:
        reasons.append(
            MatchReason(
                category="semantic",
                title="Related Background",
                explanation=f"Relevant skills and background aligned with your request ({sem_pct}% semantic similarity).",
            )
        )

    # 2. Location Reason
    loc_area_str = ", ".join(filter(None, [candidate_area, candidate_city])) or "Nearby"
    if distance_km is not None:
        if distance_km <= 5.0:
            reasons.append(
                MatchReason(
                    category="location",
                    title="Immediate Neighborhood",
                    explanation=f"Located in {loc_area_str}, only {distance_km} km away from your requested location.",
                )
            )
        elif distance_km <= 20.0:
            reasons.append(
                MatchReason(
                    category="location",
                    title="Same Metropolitan Area",
                    explanation=f"Located in {loc_area_str} ({distance_km} km away).",
                )
            )
        else:
            reasons.append(
                MatchReason(
                    category="location",
                    title="Regional Vicinity",
                    explanation=f"Located in {loc_area_str} ({distance_km} km away).",
                )
            )
    elif location_score >= 0.8:
        reasons.append(
            MatchReason(
                category="location",
                title="Same Neighborhood",
                explanation=f"Located in {loc_area_str} (matching area and city).",
            )
        )
    elif location_score >= 0.4:
        reasons.append(
            MatchReason(
                category="location",
                title="Same City",
                explanation=f"Located in {loc_area_str} within the same city.",
            )
        )

    # 3. Experience Reason
    skill_str = ", ".join(skills[:3]) if skills else ""
    if years_experience > 0 and skill_str:
        reasons.append(
            MatchReason(
                category="experience",
                title="Proven Experience & Skills",
                explanation=f"{years_experience:.1f} years of tenure with skills in {skill_str}.",
            )
        )
    elif years_experience > 0:
        reasons.append(
            MatchReason(
                category="experience",
                title="Established Local Tenure",
                explanation=f"{years_experience:.1f} years of background and community tenure.",
            )
        )
    elif skill_str:
        reasons.append(
            MatchReason(
                category="experience",
                title="Community Skills",
                explanation=f"Tagged with active skills: {skill_str}.",
            )
        )

    return reasons


def find_candidate_matches(
    db: Session,
    request_id: uuid.UUID,
    requesting_user: User,
    weights: Optional[MatchWeightsInput] = None,
    limit: int = 10,
    min_score: float = 0.0,
) -> MatchingResponse:
    """
    Real hybrid matching engine for a user request:
    1. Validates request ownership.
    2. Retrieves request vector embedding (syncing if needed).
    3. Excludes requesting user and inactive accounts.
    4. Computes native pgvector cosine distance against candidate profile embeddings.
    5. Calculates real location compatibility from coordinates / city / area.
    6. Calculates real experience compatibility from profile tenure and skills.
    7. Explicitly marks unavailable dimensions (reputation, availability) as null + UNAVAILABLE.
    8. Calculates mathematically justified final score using normalized weights of active dimensions.
    """
    req = db.query(Request).filter(Request.id == request_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found.",
        )
    if req.user_id != requesting_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access matches for this request.",
        )

    # 1. Retrieve or generate request embedding
    req_embedding_row = (
        db.query(Embedding)
        .filter(Embedding.owner_type == "request", Embedding.owner_id == req.id)
        .first()
    )
    if not req_embedding_row:
        req_embedding_row, _ = sync_user_request_embedding(db, requesting_user, req.id)

    # 2. Extract request location coordinates
    # Check if this request has a dedicated RequestLocation record (e.g. newcomer relocation target)
    req_target_loc = (
        db.query(RequestLocation)
        .filter(RequestLocation.request_id == req.id)
        .first()
    )

    req_user_loc = (
        db.query(Location)
        .filter(Location.user_id == requesting_user.id, Location.location_label == "Primary")
        .first()
    )

    if req_target_loc and req_target_loc.latitude is not None and req_target_loc.longitude is not None:
        req_lat = req_target_loc.latitude
        req_lon = req_target_loc.longitude
        req_city = req_target_loc.city or req.city or (req_user_loc.city if req_user_loc else None)
        req_area = req_target_loc.area or req.area or (req_user_loc.area if req_user_loc else None)
        req_formatted_addr = req_target_loc.formatted_address or (req_user_loc.formatted_address if req_user_loc else None)
        req_source = req_target_loc.location_source
    else:
        # Check if the request target city is different from the requester's home location
        target_city = (req_target_loc.city if req_target_loc and req_target_loc.city else None) or req.city
        user_city = req_user_loc.city if req_user_loc else None

        if target_city and user_city and target_city.strip().lower() != user_city.strip().lower():
            # Cross-city relocation scenario: target city is different from home city.
            # Do NOT inherit home city GPS coordinates for a different destination city!
            req_lat = None
            req_lon = None
        else:
            # Same city or no distinct target city: safe to use home GPS coordinates
            req_lat = req_user_loc.latitude if req_user_loc else None
            req_lon = req_user_loc.longitude if req_user_loc else None

        req_city = target_city or user_city
        req_area = (req_target_loc.area if req_target_loc and req_target_loc.area else None) or req.area or (req_user_loc.area if req_user_loc else None)
        req_formatted_addr = (req_target_loc.formatted_address if req_target_loc and req_target_loc.formatted_address else None) or (req_user_loc.formatted_address if req_user_loc else None)
        req_source = (req_target_loc.location_source if req_target_loc and req_target_loc.latitude is not None else None) or (req_user_loc.location_source if req_user_loc else "manual")

    target_location_summary = TargetLocationSummary(
        city=req_city,
        area=req_area,
        formatted_address=req_formatted_addr,
        latitude=req_lat,
        longitude=req_lon,
        location_source=req_source,
    )

    # Extract keywords from request
    req_keywords: List[str] = []
    if req.extracted_requirements and isinstance(req.extracted_requirements, dict):
        needs = req.extracted_requirements.get("needs", [])
        for n in needs:
            if isinstance(n, dict):
                req_keywords.append(n.get("item", ""))
                req_keywords.append(n.get("category", ""))
            elif isinstance(n, str):
                req_keywords.append(n)
    if req.raw_text:
        req_keywords.extend(req.raw_text.split())

    # 3. Weights setup
    w_input = weights or MatchWeightsInput()
    raw_weights = {
        "semantic": w_input.semantic,
        "location": w_input.location,
        "experience": w_input.experience,
        "reputation": w_input.reputation,
        "availability": w_input.availability,
    }

    # Active dimensions backed by real database data
    active_weight_sum = w_input.semantic + w_input.location + w_input.experience
    if active_weight_sum > 0:
        effective_weights = {
            "semantic": round(w_input.semantic / active_weight_sum, 4),
            "location": round(w_input.location / active_weight_sum, 4),
            "experience": round(w_input.experience / active_weight_sum, 4),
            "reputation": 0.0,
            "availability": 0.0,
        }
    else:
        effective_weights = {k: 0.0 for k in raw_weights}

    # 4. Ensure all active candidate users with a profile have an embedding in pgvector
    active_candidates_without_embedding = (
        db.query(User)
        .join(Profile, Profile.user_id == User.id)
        .filter(
            User.id != requesting_user.id,
            User.is_active == True,
            ~User.id.in_(
                db.query(Embedding.owner_id).filter(Embedding.owner_type == "profile")
            ),
        )
        .all()
    )
    for c_user in active_candidates_without_embedding:
        sync_user_profile_embedding(db, c_user)

    # 5. Native PostgreSQL pgvector cosine distance query
    dist_expr = Embedding.embedding.cosine_distance(req_embedding_row.embedding)

    stmt = (
        select(Embedding.owner_id, dist_expr.label("distance"))
        .join(User, User.id == Embedding.owner_id)
        .join(Profile, Profile.user_id == User.id)
        .filter(
            Embedding.owner_type == "profile",
            Embedding.owner_id != requesting_user.id,
            User.is_active == True,
        )
        .order_by(dist_expr.asc())
    )

    candidate_vector_rows = db.execute(stmt).fetchall()

    candidates: List[HelperCandidate] = []

    for row in candidate_vector_rows:
        cand_user_id = row[0]
        cos_dist = float(row[1])
        # Cosine similarity in [0.0, 1.0]
        semantic_score = max(0.0, min(1.0, 1.0 - cos_dist))

        # Retrieve candidate user, profile, location, skills
        user = db.query(User).filter(User.id == cand_user_id).first()
        if not user:
            continue

        cand_profile = db.query(Profile).filter(Profile.user_id == cand_user_id).first()
        cand_loc = (
            db.query(Location)
            .filter(Location.user_id == cand_user_id, Location.location_label == "Primary")
            .first()
        )
        skills_raw = (
            db.query(Skill.name, UserSkill.proficiency, UserSkill.years_experience)
            .join(UserSkill, UserSkill.skill_id == Skill.id)
            .filter(UserSkill.user_id == cand_user_id)
            .order_by(Skill.name.asc())
            .all()
        )

        cand_skills_list = [s[0] for s in skills_raw]

        # Location compatibility
        cand_lat = cand_loc.latitude if cand_loc else None
        cand_lon = cand_loc.longitude if cand_loc else None
        cand_city = cand_loc.city if cand_loc else None
        cand_area = cand_loc.area if cand_loc else None

        location_score, distance_km = calculate_location_score(
            req_lat=req_lat,
            req_lon=req_lon,
            cand_lat=cand_lat,
            cand_lon=cand_lon,
            req_city=req_city,
            req_area=req_area,
            cand_city=cand_city,
            cand_area=cand_area,
        )

        # Experience compatibility
        experience_score = calculate_experience_score(
            profile=cand_profile,
            skills_data=skills_raw,
            request_keywords=req_keywords,
        )

        # Calculate mathematically justified composite score
        if active_weight_sum > 0:
            final_score = (
                w_input.semantic * semantic_score
                + w_input.location * location_score
                + w_input.experience * experience_score
            ) / active_weight_sum
        else:
            final_score = 0.0

        if final_score < min_score:
            continue

        # Generate reasons
        years_exp = cand_profile.years_experience if cand_profile and cand_profile.years_experience else 0.0
        reasons = generate_match_reasons(
            semantic_score=semantic_score,
            location_score=location_score,
            experience_score=experience_score,
            distance_km=distance_km,
            candidate_city=cand_city,
            candidate_area=cand_area,
            years_experience=years_exp,
            skills=cand_skills_list,
        )

        # Candidate name without exposing private email or phone
        display_name = user.name or user.email.split("@")[0].capitalize()

        # Privacy: NEVER expose candidate's exact raw coordinates or street address
        # Approximate coords rounded to 2 decimal places (~1.1 km area precision)
        approx_lat = round(cand_lat, 2) if cand_lat is not None else None
        approx_lon = round(cand_lon, 2) if cand_lon is not None else None

        candidate_item = HelperCandidate(
            user_id=cand_user_id,
            name=display_name,
            headline=cand_profile.headline if cand_profile else None,
            bio=cand_profile.bio if cand_profile else None,
            city=cand_city,
            area=cand_area,
            distance_km=distance_km,
            approximate_latitude=approx_lat,
            approximate_longitude=approx_lon,
            route_info=None,
            skills=cand_skills_list,
            scores=MatchScores(
                semantic_score=round(semantic_score, 4),
                location_score=round(location_score, 4),
                experience_score=round(experience_score, 4),
                reputation_score=None,
                availability_score=None,
                final_score=round(final_score, 4),
            ),
            dimension_statuses=DimensionStatuses(
                semantic=DimensionStatusEnum.ACTIVE,
                location=DimensionStatusEnum.ACTIVE,
                experience=DimensionStatusEnum.ACTIVE,
                reputation=DimensionStatusEnum.UNAVAILABLE,
                availability=DimensionStatusEnum.UNAVAILABLE,
            ),
            reasons=reasons,
            is_available_for_help=cand_profile.availability if cand_profile else None,
        )
        candidates.append(candidate_item)

    # Sort descending by final score
    candidates.sort(key=lambda c: c.scores.final_score, reverse=True)

    # Slice to limit
    trimmed_candidates = candidates[:limit]

    # Compute route travel info for top candidates (Top-5) when coordinates are available
    if req_lat is not None and req_lon is not None:
        for cand in trimmed_candidates[:5]:
            c_loc = (
                db.query(Location)
                .filter(Location.user_id == cand.user_id, Location.location_label == "Primary")
                .first()
            )
            if c_loc and c_loc.latitude is not None and c_loc.longitude is not None:
                cand.route_info = google_maps_service.compute_route_travel(
                    origin_lat=c_loc.latitude,
                    origin_lon=c_loc.longitude,
                    dest_lat=req_lat,
                    dest_lon=req_lon,
                )

    return MatchingResponse(
        request_id=req.id,
        target_location=target_location_summary,
        total_candidates_evaluated=len(candidate_vector_rows),
        matches=trimmed_candidates,
        weights_used=WeightsSummary(raw=raw_weights, effective=effective_weights),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
