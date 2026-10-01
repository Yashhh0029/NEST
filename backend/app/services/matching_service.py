from datetime import datetime, timezone, timedelta
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
from app.models.availability import (
    HelperAvailabilityException,
    HelperAvailabilitySlot,
)
from app.services.availability_service import get_derived_capacity_status
from app.services.embedding_repository import (
    sync_user_profile_embedding,
    sync_user_request_embedding,
)
from app.services.google_maps_service import google_maps_service
from app.services.safety_service import get_blocked_user_ids


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


def calculate_availability_score(
    db: Session,
    helper_id: uuid.UUID,
    req: Request,
    cand_profile: Optional[Profile],
) -> Tuple[Optional[float], DimensionStatusEnum, Optional[str]]:
    """
    Computes deterministic availability score in [0.0, 1.0] based on helper schedule,
    derived capacity, blackout dates, and newcomer request timing preferences.
    """
    # 1. Check if helper has configured any active recurring slots
    slots = (
        db.query(HelperAvailabilitySlot)
        .filter(
            HelperAvailabilitySlot.user_id == helper_id,
            HelperAvailabilitySlot.is_active == True,
        )
        .all()
    )
    if not slots:
        return None, DimensionStatusEnum.UNAVAILABLE, "Availability schedule not published"

    # 2. Check derived capacity
    cap_status, active_count = get_derived_capacity_status(db, helper_id, cand_profile)
    if cap_status == "NOT_ACCEPTING":
        return 0.0, DimensionStatusEnum.ACTIVE, "Helper is currently not accepting new assistance sessions"
    if cap_status == "AT_CAPACITY":
        max_s = cand_profile.max_weekly_sessions if cand_profile else 3
        return 0.0, DimensionStatusEnum.ACTIVE, f"Helper is currently at full capacity for the week ({active_count}/{max_s} sessions)"

    # 3. Request-Time Aware matching
    # Scenario A: Newcomer specified a preferred date
    if req.preferred_date:
        # Check blackout exception on exact date
        blackout = (
            db.query(HelperAvailabilityException)
            .filter(
                HelperAvailabilityException.user_id == helper_id,
                HelperAvailabilityException.exception_date == req.preferred_date,
                HelperAvailabilityException.is_available == False,
            )
            .first()
        )
        day_of_week = req.preferred_date.weekday()  # 0=Monday, 6=Sunday
        day_slots = [s for s in slots if s.day_of_week == day_of_week]

        exact_match = False
        exact_score = 0.0
        exact_reason = ""

        if not blackout and day_slots:
            if req.preferred_start_time and req.preferred_end_time:
                req_start_m = req.preferred_start_time.hour * 60 + req.preferred_start_time.minute
                req_end_m = req.preferred_end_time.hour * 60 + req.preferred_end_time.minute
                req_duration = max(1, req_end_m - req_start_m)

                total_overlap_m = 0
                for s in day_slots:
                    slot_start_m = s.start_time.hour * 60 + s.start_time.minute
                    slot_end_m = s.end_time.hour * 60 + s.end_time.minute
                    overlap = max(0, min(slot_end_m, req_end_m) - max(slot_start_m, req_start_m))
                    total_overlap_m += overlap

                score = min(1.0, total_overlap_m / req_duration)
                if score > 0:
                    exact_match = True
                    exact_score = round(score, 4)
                    if score >= 0.95:
                        exact_reason = f"Full schedule match on {req.preferred_date.strftime('%A')} ({req.preferred_start_time.strftime('%H:%M')}-{req.preferred_end_time.strftime('%H:%M')})"
                    else:
                        exact_reason = f"Partial schedule overlap ({int(score * 100)}%) on {req.preferred_date.strftime('%A')}"
            else:
                exact_match = True
                exact_score = 1.0
                day_name = req.preferred_date.strftime("%A")
                exact_reason = f"Active schedule available on {day_name} ({len(day_slots)} slots)"

        if exact_match:
            return exact_score, DimensionStatusEnum.ACTIVE, exact_reason

        # If no exact match, check flexible window if requester indicated flexibility
        is_flexible = getattr(req, "is_time_flexible", False)
        window_days = getattr(req, "flexibility_window_days", None)
        if is_flexible:
            max_window = window_days if (window_days and window_days > 0) else 2
            offsets = []
            for d in range(1, max_window + 1):
                offsets.append(d)
                offsets.append(-d)

            for offset in offsets:
                cand_date = req.preferred_date + timedelta(days=offset)
                cand_blackout = (
                    db.query(HelperAvailabilityException)
                    .filter(
                        HelperAvailabilityException.user_id == helper_id,
                        HelperAvailabilityException.exception_date == cand_date,
                        HelperAvailabilityException.is_available == False,
                    )
                    .first()
                )
                if cand_blackout:
                    continue

                cand_day_of_week = cand_date.weekday()
                cand_slots = [s for s in slots if s.day_of_week == cand_day_of_week]
                if not cand_slots:
                    continue

                cand_score = 0.0
                if req.preferred_start_time and req.preferred_end_time:
                    req_start_m = req.preferred_start_time.hour * 60 + req.preferred_start_time.minute
                    req_end_m = req.preferred_end_time.hour * 60 + req.preferred_end_time.minute
                    req_duration = max(1, req_end_m - req_start_m)
                    total_overlap_m = 0
                    for s in cand_slots:
                        slot_start_m = s.start_time.hour * 60 + s.start_time.minute
                        slot_end_m = s.end_time.hour * 60 + s.end_time.minute
                        overlap = max(0, min(slot_end_m, req_end_m) - max(slot_start_m, req_start_m))
                        total_overlap_m += overlap
                    if total_overlap_m <= 0:
                        continue
                    cand_score = min(1.0, total_overlap_m / req_duration)
                else:
                    cand_score = 1.0

                if cand_score > 0:
                    penalty = max(0.5, 1.0 - (0.10 * abs(offset)))
                    discounted_score = round(cand_score * penalty, 4)
                    rel = "day after" if offset == 1 else ("days after" if offset > 0 else ("day before" if offset == -1 else "days before"))
                    flex_reason = f"Available within flexibility window on {cand_date.strftime('%A')} ({abs(offset)} {rel} requested date)"
                    return discounted_score, DimensionStatusEnum.ACTIVE, flex_reason

        # Return failure reason for exact date
        if blackout:
            return 0.0, DimensionStatusEnum.ACTIVE, f"Helper has a scheduled blackout date on {req.preferred_date}"
        if not day_slots:
            day_name = req.preferred_date.strftime("%A")
            return 0.0, DimensionStatusEnum.ACTIVE, f"Helper has no active hours on {day_name}s"
        return 0.0, DimensionStatusEnum.ACTIVE, f"No schedule overlap with requested hours on {req.preferred_date.strftime('%A')}"

    # Scenario B: Preferred days of week specified
    if req.preferred_days_of_week and isinstance(req.preferred_days_of_week, list) and len(req.preferred_days_of_week) > 0:
        helper_days = set(s.day_of_week for s in slots)
        req_days = set(req.preferred_days_of_week)
        intersection = req_days.intersection(helper_days)
        score = len(intersection) / len(req_days)
        if score > 0:
            reason = f"Available on {len(intersection)} of {len(req_days)} requested preferred days"
        else:
            reason = "No availability matching requested preferred days of the week"
        return round(score, 4), DimensionStatusEnum.ACTIVE, reason

    # Scenario C: Flexible / Unspecified timing preference
    # General availability readiness: helper is available and accepting sessions
    total_weekly_minutes = sum(
        (s.end_time.hour * 60 + s.end_time.minute) - (s.start_time.hour * 60 + s.start_time.minute)
        for s in slots
    )
    total_hours = total_weekly_minutes / 60.0
    score = max(0.7, min(1.0, 0.7 + 0.3 * (total_hours / 10.0)))
    reason = f"Published weekly availability ({total_hours:.1f} hours across {len(slots)} slots)"
    return round(score, 4), DimensionStatusEnum.ACTIVE, reason


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
            User.email_verified == True,
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

    blocked_user_ids = get_blocked_user_ids(db, requesting_user.id)

    stmt = (
        select(Embedding.owner_id, dist_expr.label("distance"))
        .join(User, User.id == Embedding.owner_id)
        .join(Profile, Profile.user_id == User.id)
        .filter(
            Embedding.owner_type == "profile",
            Embedding.owner_id != requesting_user.id,
            User.is_active == True,
            User.email_verified == True,
        )
    )
    if blocked_user_ids:
        stmt = stmt.filter(~Embedding.owner_id.in_(list(blocked_user_ids)))

    stmt = stmt.order_by(dist_expr.asc())

    candidate_vector_rows = db.execute(stmt).fetchall()

    candidates: List[HelperCandidate] = []

    for row in candidate_vector_rows:
        cand_user_id = row[0]
        if cand_user_id in blocked_user_ids:
            continue
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

        # Real Reputation evaluation (Phase 9)
        from app.services.review_service import get_user_reputation
        rep_summary = get_user_reputation(db, cand_user_id)
        has_reputation = rep_summary.review_count > 0 and rep_summary.average_rating is not None
        if has_reputation:
            # Normalized score: 1.0 -> 0.0, 5.0 -> 1.0
            reputation_score = max(0.0, min(1.0, (rep_summary.average_rating - 1.0) / 4.0))
            reputation_status = DimensionStatusEnum.ACTIVE
        else:
            reputation_score = None
            reputation_status = DimensionStatusEnum.UNAVAILABLE

        # Real Availability evaluation (Phase 14)
        avail_score, avail_status, avail_reason = calculate_availability_score(
            db=db,
            helper_id=cand_user_id,
            req=req,
            cand_profile=cand_profile,
        )
        has_availability = avail_score is not None

        # Build active weights dynamically with dynamic redistribution
        active_weights_cand = w_input.semantic + w_input.location + w_input.experience
        if has_reputation:
            active_weights_cand += w_input.reputation
        if has_availability:
            active_weights_cand += w_input.availability

        if active_weights_cand > 0:
            numerator = (
                w_input.semantic * semantic_score
                + w_input.location * location_score
                + w_input.experience * experience_score
            )
            if has_reputation:
                numerator += w_input.reputation * reputation_score
            if has_availability:
                numerator += w_input.availability * avail_score
            final_score = numerator / active_weights_cand
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

        if has_reputation:
            reasons.append(
                MatchReason(
                    category="reputation",
                    title="Community Endorsement",
                    explanation=f"Rated {rep_summary.average_rating:.1f} stars across {rep_summary.review_count} verified reviews.",
                )
            )

        if avail_reason:
            reasons.append(
                MatchReason(
                    category="availability",
                    title="Schedule Compatibility",
                    explanation=avail_reason,
                )
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
                reputation_score=round(reputation_score, 4) if reputation_score is not None else None,
                availability_score=round(avail_score, 4) if avail_score is not None else None,
                final_score=round(final_score, 4),
            ),
            dimension_statuses=DimensionStatuses(
                semantic=DimensionStatusEnum.ACTIVE,
                location=DimensionStatusEnum.ACTIVE,
                experience=DimensionStatusEnum.ACTIVE,
                reputation=reputation_status,
                availability=avail_status,
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
