import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.request import Request
from app.models.user import User
from app.schemas.request import RequestCreate, RequestUpdate
from app.services.location_service import resolve_and_upsert_request_location
from app.services.request_parser import parse_request
from app.services.request_state_machine import validate_request_transition


def create_user_request(db: Session, user: User, req_in: RequestCreate) -> Request:
    """Parse natural language request and persist structured requirements and target location."""
    parsed = parse_request(req_in.text)

    final_city = req_in.target_city or parsed.location.city
    final_area = req_in.target_area or parsed.location.area

    new_request = Request(
        user_id=user.id,
        raw_text=req_in.text,
        intent=parsed.intent,
        status="OPEN",
        city=final_city,
        area=final_area,
        state=parsed.location.state,
        country=parsed.location.country or "India",
        budget_amount=parsed.budget.amount if parsed.budget else None,
        budget_currency=parsed.budget.currency if parsed.budget else None,
        budget_period=parsed.budget.period if parsed.budget else None,
        budget_operator=parsed.budget.operator if parsed.budget else None,
        extracted_requirements=parsed.model_dump(),
        preferences=parsed.preferences,
        user_context=parsed.user_context,
        extraction_method=parsed.extraction_method,
        preferred_date=req_in.preferred_date,
        preferred_start_time=req_in.preferred_start_time,
        preferred_end_time=req_in.preferred_end_time,
        requester_timezone=req_in.requester_timezone or "Asia/Kolkata",
        is_time_flexible=req_in.is_time_flexible if req_in.is_time_flexible is not None else True,
        flexibility_window_days=req_in.flexibility_window_days if req_in.flexibility_window_days is not None else 3,
        preferred_days_of_week=req_in.preferred_days_of_week if req_in.preferred_days_of_week is not None else [],
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    # Automatically resolve and persist request target location
    resolve_and_upsert_request_location(
        db=db,
        request_id=new_request.id,
        user=user,
        city_hint=final_city,
        area_hint=final_area,
        google_place_id=req_in.target_google_place_id,
        latitude=req_in.target_latitude,
        longitude=req_in.target_longitude,
        formatted_address=req_in.target_formatted_address,
        display_name=req_in.target_display_name,
    )

    return new_request


def get_user_requests(db: Session, user: User) -> List[Request]:
    """Retrieve all requests created by the authenticated user."""
    return (
        db.query(Request)
        .filter(Request.user_id == user.id)
        .order_by(Request.created_at.desc())
        .all()
    )


def get_user_request_by_id(
    db: Session, user: User, request_id: uuid.UUID
) -> Request:
    """Retrieve specific request by ID, enforcing strict user ownership."""
    req = db.query(Request).filter(Request.id == request_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found.",
        )
    if req.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this request.",
        )
    return req


def update_user_request(
    db: Session, user: User, request_id: uuid.UUID, update_in: RequestUpdate
) -> Request:
    """Update user request fields; re-parses requirements if text changed."""
    req = get_user_request_by_id(db, user, request_id)

    if update_in.text is not None and update_in.text.strip():
        parsed = parse_request(update_in.text)
        req.raw_text = update_in.text
        req.city = parsed.location.city
        req.area = parsed.location.area
        req.state = parsed.location.state
        req.country = parsed.location.country or "India"
        req.budget_amount = parsed.budget.amount if parsed.budget else None
        req.budget_currency = parsed.budget.currency if parsed.budget else None
        req.budget_period = parsed.budget.period if parsed.budget else None
        req.budget_operator = parsed.budget.operator if parsed.budget else None
        req.extracted_requirements = parsed.model_dump()
        req.preferences = parsed.preferences
        req.user_context = parsed.user_context

        # Update target location
        resolve_and_upsert_request_location(
            db=db,
            request_id=req.id,
            user=user,
            city_hint=parsed.location.city,
            area_hint=parsed.location.area,
        )

    if update_in.status is not None:
        target_status = update_in.status.upper().strip()
        validate_request_transition(
            db=db,
            request=req,
            target_status=target_status,
            user=user,
            is_independent_resolution=bool(update_in.is_independent_resolution),
            resolution_note=update_in.resolution_summary,
        )
        req.status = target_status
        if target_status == "RESOLVED":
            req.resolved_at = datetime.now(timezone.utc)
            if update_in.resolution_summary:
                req.resolution_summary = update_in.resolution_summary.strip()

    if update_in.preferred_date is not None:
        req.preferred_date = update_in.preferred_date
    if update_in.preferred_start_time is not None:
        req.preferred_start_time = update_in.preferred_start_time
    if update_in.preferred_end_time is not None:
        req.preferred_end_time = update_in.preferred_end_time
    if update_in.requester_timezone is not None:
        req.requester_timezone = update_in.requester_timezone
    if update_in.is_time_flexible is not None:
        req.is_time_flexible = update_in.is_time_flexible
    if update_in.flexibility_window_days is not None:
        req.flexibility_window_days = update_in.flexibility_window_days
    if update_in.preferred_days_of_week is not None:
        req.preferred_days_of_week = update_in.preferred_days_of_week

    db.commit()
    db.refresh(req)
    return req


def delete_user_request(
    db: Session, user: User, request_id: uuid.UUID
) -> bool:
    """Delete a user's request, enforcing strict ownership."""
    req = get_user_request_by_id(db, user, request_id)
    db.delete(req)
    db.commit()
    return True


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Haversine distance in kilometers between two lat/lon coordinates."""
    import math
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def get_nearby_requests_for_helper(
    db: Session,
    helper: User,
    radius_km: Optional[float] = None,
    limit: int = 50,
):
    """
    Retrieve open newcomer requests relevant to this helper.
    Excludes helper's own requests and users with active safety blocks.
    Computes real proximity and generates truthful explanation reasons.
    """
    from typing import Set
    from app.models.safety import Block
    from app.models.location import Location
    from app.models.request_location import RequestLocation
    from app.schemas.request import NearbyRequestItem

    # 1. Safety exclusions: bidirectional blocks
    blocked_subq = db.query(Block.blocked_id).filter(Block.blocker_id == helper.id)
    blocker_subq = db.query(Block.blocker_id).filter(Block.blocked_id == helper.id)
    blocked_ids = set([r[0] for r in blocked_subq.all()] + [r[0] for r in blocker_subq.all()])
    blocked_ids.add(helper.id)

    # 2. Get helper's location & profile context
    helper_loc = (
        db.query(Location)
        .filter(Location.user_id == helper.id, Location.location_label == "Primary")
        .first()
    )
    if not helper_loc:
        helper_loc = db.query(Location).filter(Location.user_id == helper.id).first()

    helper_city = (helper_loc.city or "").strip().lower() if helper_loc else ""
    helper_lat = float(helper_loc.latitude) if helper_loc and helper_loc.latitude is not None else None
    helper_lon = float(helper_loc.longitude) if helper_loc and helper_loc.longitude is not None else None

    # Helper skills and profile keywords
    helper_keywords: Set[str] = set()
    if helper.profile:
        if helper.profile.help_description:
            helper_keywords.update(helper.profile.help_description.lower().split())
        if helper.profile.headline:
            helper_keywords.update(helper.profile.headline.lower().split())
        if helper.profile.occupation:
            helper_keywords.update(helper.profile.occupation.lower().split())

    # 3. Query open requests from active, email-verified requesters
    open_requests = (
        db.query(Request)
        .join(User, User.id == Request.user_id)
        .filter(
            Request.status == "OPEN",
            User.is_active == True,
            User.email_verified == True,
            ~Request.user_id.in_(blocked_ids),
        )
        .order_by(Request.created_at.desc())
        .limit(100)
        .all()
    )

    items = []
    for req in open_requests:
        req_user = db.query(User).filter(User.id == req.user_id).first()
        requester_name = req_user.name if req_user else "Newcomer"

        # Check location
        req_loc = db.query(RequestLocation).filter(RequestLocation.request_id == req.id).first()
        dist_km = None
        if (
            helper_lat is not None
            and helper_lon is not None
            and req_loc
            and req_loc.latitude is not None
            and req_loc.longitude is not None
        ):
            dist_km = round(_haversine_distance(helper_lat, helper_lon, float(req_loc.latitude), float(req_loc.longitude)), 1)
            if radius_km is not None and dist_km > radius_km:
                continue

        # Extract needs
        extracted = req.extracted_requirements or {}
        needs_list = []
        if isinstance(extracted, dict):
            raw_needs = extracted.get("needs", [])
            if isinstance(raw_needs, list):
                for n in raw_needs:
                    if isinstance(n, dict) and "category" in n:
                        needs_list.append(str(n["category"]).capitalize())
                    elif isinstance(n, str):
                        needs_list.append(n.capitalize())

        # Generate truthful reasons
        reasons = []
        if dist_km is not None:
            reasons.append(f"Located within {dist_km} km")
        elif req.city and helper_city and req.city.strip().lower() == helper_city:
            reasons.append(f"Located in your city ({req.city})")

        # Skill / topic overlap
        for n in needs_list:
            if n.lower() in helper_keywords or any(n.lower() in kw for kw in helper_keywords):
                reasons.append(f"Matches your background in {n}")
                break

        if not reasons:
            reasons.append("Open request awaiting a local guide")

        item = NearbyRequestItem(
            id=req.id,
            user_id=req.user_id,
            requester_name=requester_name,
            raw_text=req.raw_text,
            intent=req.intent,
            status=req.status,
            city=req.city,
            area=req.area,
            state=req.state,
            country=req.country,
            budget_amount=float(req.budget_amount) if req.budget_amount is not None else None,
            budget_currency=req.budget_currency,
            budget_period=req.budget_period,
            preferred_date=req.preferred_date,
            preferred_start_time=req.preferred_start_time,
            preferred_end_time=req.preferred_end_time,
            requester_timezone=req.requester_timezone,
            is_time_flexible=req.is_time_flexible,
            needs=needs_list,
            distance_km=dist_km,
            match_reasons=reasons,
            created_at=req.created_at,
        )
        items.append(item)

    # Sort items: proximity first (if known), then match reasons count, then creation time
    items.sort(
        key=lambda x: (
            x.distance_km if x.distance_km is not None else 999999.0,
            -len(x.match_reasons),
            -x.created_at.timestamp(),
        )
    )

    return items[:limit]
