from typing import List
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.intelligence import (
    NeedProgressUpdate,
    RequestIntelligenceResponse,
    RequestResolvePayload,
    SavedResourceCreate,
    SavedResourceResponse,
)
from app.services import intelligence_service

router = APIRouter(prefix="/requests", tags=["Request Intelligence & Discovery"])


@router.get(
    "/{request_id}/intelligence",
    response_model=RequestIntelligenceResponse,
    summary="Unified Request Intelligence (People, Community, Resources, Connections)",
)
def get_request_intelligence_endpoint(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve unified discovery and intelligence for a newcomer request.
    Aggregates People, Community Q&As, Local Resources, and Active Connections
    organized by structured need, with factual explainability and action plan.
    """
    return intelligence_service.get_request_intelligence(db, request_id, current_user)


@router.patch(
    "/{request_id}/need-progress",
    response_model=RequestIntelligenceResponse,
    summary="Update need progress status with entity validation",
)
def update_need_progress_endpoint(
    request_id: uuid.UUID,
    payload: NeedProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update progress on a specific request need category.
    Validates resolved_entity_id server-side to prevent unauthorized injection.
    """
    return intelligence_service.update_need_progress(db, request_id, current_user, payload)


@router.post(
    "/{request_id}/resolve",
    response_model=RequestIntelligenceResponse,
    summary="Mark overall request as RESOLVED",
)
def resolve_request_endpoint(
    request_id: uuid.UUID,
    payload: RequestResolvePayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Explicitly mark a request as RESOLVED with an optional closing note.
    Transitions untracked needs to RESOLVED.
    """
    return intelligence_service.resolve_overall_request(db, request_id, current_user, payload)


@router.post(
    "/{request_id}/saved-resources",
    response_model=SavedResourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bookmark a discovered resource to a request",
)
def save_resource_endpoint(
    request_id: uuid.UUID,
    payload: SavedResourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Save / bookmark a discovered place to a request.
    Stores public place metadata only (no private coordinates).
    """
    return intelligence_service.save_resource_for_request(db, request_id, current_user, payload)


@router.get(
    "/{request_id}/saved-resources",
    response_model=List[SavedResourceResponse],
    summary="List all saved resources for a request",
)
def list_saved_resources_endpoint(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all saved / bookmarked resources for a request."""
    return intelligence_service.list_saved_resources_for_request(db, request_id, current_user)


@router.delete(
    "/{request_id}/saved-resources/{place_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a saved resource bookmark from a request",
)
def delete_saved_resource_endpoint(
    request_id: uuid.UUID,
    place_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a saved resource bookmark from a request."""
    intelligence_service.delete_saved_resource_for_request(db, request_id, place_id, current_user)
