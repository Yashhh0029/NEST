from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionListResponse,
    ConnectionResponse,
    ConnectionStatusUpdate,
)
from app.services.connection_service import (
    create_connection_request,
    get_connection_by_id,
    get_user_connections,
    update_connection_status,
)

router = APIRouter(tags=["Connections"])


@router.post(
    "",
    response_model=ConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a connection request to a helper",
)
def create_connection(
    payload: ConnectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConnectionResponse:
    """
    Newcomer sends a connection request to a candidate helper for an open request.
    """
    return create_connection_request(db, current_user, payload)


@router.get(
    "",
    response_model=ConnectionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all connections for the current user",
)
def list_connections(
    status: Optional[str] = Query(None, description="Filter by status: PENDING, ACCEPTED, DECLINED, CANCELLED"),
    role: Optional[str] = Query(None, description="Filter by role: requester or helper"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConnectionListResponse:
    """
    Retrieve all connections involving the authenticated user as either requester or helper.
    """
    conns = get_user_connections(db, current_user, status_filter=status, role_filter=role)
    return ConnectionListResponse(total=len(conns), connections=conns)


@router.get(
    "/{connection_id}",
    response_model=ConnectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single connection by ID",
)
def get_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConnectionResponse:
    """
    Get detailed information about a specific connection.
    User must be either the requester or helper.
    """
    return get_connection_by_id(db, connection_id, current_user)


@router.patch(
    "/{connection_id}",
    response_model=ConnectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update connection status (accept, decline, cancel)",
)
def update_status(
    connection_id: uuid.UUID,
    payload: ConnectionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConnectionResponse:
    """
    Update connection lifecycle state:
    - Designated helper can 'accept' or 'decline'.
    - Requester can 'cancel'.
    """
    return update_connection_status(db, connection_id, current_user, payload.action)
