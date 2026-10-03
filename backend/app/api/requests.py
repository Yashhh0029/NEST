import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.request import (
    NearbyRequestItem,
    RequestCreate,
    RequestParse,
    RequestParseResponse,
    RequestResponse,
    RequestUpdate,
)
from app.services.request_parser import parse_request
from app.services.request_service import (
    create_user_request,
    delete_user_request,
    get_nearby_requests_for_helper,
    get_request_with_privacy,
    get_user_request_by_id,
    get_user_requests,
    update_user_request,
)

router = APIRouter(prefix="/requests", tags=["Requests & NLP Extraction"])


@router.post(
    "/parse",
    response_model=RequestParseResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview NLP extraction without database persistence",
    description="Statelessly parses natural-language newcomer requirements for preview or testing.",
)
def parse_request_preview(payload: RequestParse) -> RequestParseResponse:
    """Preview deterministic extraction from user text without persistence."""
    parsed = parse_request(payload.text)
    return RequestParseResponse(raw_text=payload.text, extracted=parsed)


@router.post(
    "",
    response_model=RequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and persist a new requirement request",
    description="Authenticates newcomer, preserves raw text, runs deterministic NLP extraction, and persists structured requirements in PostgreSQL.",
)
def create_request(
    payload: RequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RequestResponse:
    """Create and persist a newcomer request."""
    req = create_user_request(db, current_user, payload)
    return RequestResponse.model_validate(req)


@router.get(
    "",
    response_model=List[RequestResponse],
    status_code=status.HTTP_200_OK,
    summary="List all requests created by the authenticated user",
    description="Retrieves request history for the currently logged-in user.",
)
def list_my_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[RequestResponse]:
    """List current user's requests."""
    requests = get_user_requests(db, current_user)
    return [RequestResponse.model_validate(r) for r in requests]


@router.get(
    "/nearby",
    response_model=List[NearbyRequestItem],
    status_code=status.HTTP_200_OK,
    summary="List nearby open newcomer requests for helper feed",
    description="Returns open newcomer requests with proximity calculations and privacy-safe summaries for enrolled helpers.",
)
def get_nearby_requests(
    radius_km: Optional[float] = Query(None, description="Optional search radius in km"),
    limit: int = Query(50, ge=1, le=100, description="Max number of requests to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[NearbyRequestItem]:
    """Get nearby open requests for helper."""
    return get_nearby_requests_for_helper(db, current_user, radius_km=radius_km, limit=limit)


@router.get(
    "/{request_id}",
    response_model=RequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve request by ID",
    description="Retrieves a specific request owned by the authenticated user.",
)
def get_request(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RequestResponse:
    """Get single request by ID with privacy preservation for community helpers."""
    return get_request_with_privacy(db, current_user, request_id)


@router.patch(
    "/{request_id}",
    response_model=RequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Update request text or status",
    description="Updates request details; if text is changed, requirements are automatically re-parsed.",
)
def patch_request(
    request_id: uuid.UUID,
    payload: RequestUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RequestResponse:
    """Update user request."""
    req = update_user_request(db, current_user, request_id, payload)
    return RequestResponse.model_validate(req)


@router.delete(
    "/{request_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a request",
    description="Deletes a request owned by the authenticated user.",
)
def delete_request(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete user request."""
    delete_user_request(db, current_user, request_id)
    return {"detail": "Request deleted successfully"}
