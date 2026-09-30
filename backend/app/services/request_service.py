import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.request import Request
from app.models.user import User
from app.schemas.request import RequestCreate, RequestUpdate
from app.services.location_service import resolve_and_upsert_request_location
from app.services.request_parser import parse_request


def create_user_request(db: Session, user: User, req_in: RequestCreate) -> Request:
    """Parse natural language request and persist structured requirements and target location."""
    parsed = parse_request(req_in.text)

    new_request = Request(
        user_id=user.id,
        raw_text=req_in.text,
        intent=parsed.intent,
        status="OPEN",
        city=parsed.location.city,
        area=parsed.location.area,
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
        city_hint=parsed.location.city,
        area_hint=parsed.location.area,
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
        req.status = update_in.status.upper()

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
