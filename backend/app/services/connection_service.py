from datetime import datetime, timezone
from typing import List, Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.connection import Connection, ConnectionStatus
from app.models.location import Location
from app.models.profile import Profile
from app.models.request import Request
from app.models.user import User
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionRequestSummary,
    ConnectionResponse,
    ConnectionStatusEnum,
    ConnectionUserSummary,
)


def _hydrate_user_summary(db: Session, user: User) -> ConnectionUserSummary:
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    location = (
        db.query(Location)
        .filter(Location.user_id == user.id, Location.location_label == "Primary")
        .first()
    )
    return ConnectionUserSummary(
        id=user.id,
        name=user.name or user.email.split("@")[0].capitalize(),
        headline=profile.headline if profile else None,
        city=location.city if location else None,
        area=location.area if location else None,
    )


def _hydrate_connection_response(db: Session, conn: Connection) -> ConnectionResponse:
    requester_summary = _hydrate_user_summary(db, conn.requester) if conn.requester else None
    helper_summary = _hydrate_user_summary(db, conn.helper) if conn.helper else None
    request_summary = (
        ConnectionRequestSummary(
            id=conn.request.id,
            raw_text=conn.request.raw_text,
            city=conn.request.city,
            area=conn.request.area,
            intent=conn.request.intent,
        )
        if conn.request
        else None
    )

    return ConnectionResponse(
        id=conn.id,
        request_id=conn.request_id,
        requester_id=conn.requester_id,
        helper_id=conn.helper_id,
        status=ConnectionStatusEnum(conn.status),
        initial_message=conn.initial_message,
        created_at=conn.created_at,
        updated_at=conn.updated_at,
        accepted_at=conn.accepted_at,
        declined_at=conn.declined_at,
        requester=requester_summary,
        helper=helper_summary,
        request=request_summary,
    )


def create_connection_request(
    db: Session,
    current_user: User,
    payload: ConnectionCreate,
) -> ConnectionResponse:
    """
    Initiate a real connection request from a newcomer to a candidate helper.
    """
    # 1. Requester cannot connect to themselves
    if payload.helper_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot send a connection request to yourself.",
        )

    # 2. Verify request exists and belongs to current user
    req = db.query(Request).filter(Request.id == payload.request_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found.",
        )
    if req.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only connect with helpers for your own requests.",
        )

    # 3. Verify helper exists and is active
    helper = db.query(User).filter(User.id == payload.helper_id, User.is_active == True).first()
    if not helper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Helper user not found or account is inactive.",
        )

    # 4. Check for existing connection between this requester, helper, and request
    existing_conn = (
        db.query(Connection)
        .filter(
            Connection.request_id == payload.request_id,
            Connection.requester_id == current_user.id,
            Connection.helper_id == payload.helper_id,
        )
        .first()
    )

    now = datetime.now(timezone.utc)

    if existing_conn:
        if existing_conn.status in [ConnectionStatus.PENDING.value, ConnectionStatus.ACCEPTED.value]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A connection request already exists with status: {existing_conn.status}",
            )
        # If previously declined or cancelled, permit re-requesting
        existing_conn.status = ConnectionStatus.PENDING.value
        existing_conn.initial_message = payload.initial_message
        existing_conn.updated_at = now
        existing_conn.accepted_at = None
        existing_conn.declined_at = None
        db.commit()
        db.refresh(existing_conn)
        return _hydrate_connection_response(db, existing_conn)

    # 5. Create new Connection
    new_conn = Connection(
        request_id=payload.request_id,
        requester_id=current_user.id,
        helper_id=payload.helper_id,
        status=ConnectionStatus.PENDING.value,
        initial_message=payload.initial_message,
        created_at=now,
        updated_at=now,
    )
    db.add(new_conn)
    db.commit()
    db.refresh(new_conn)

    return _hydrate_connection_response(db, new_conn)


def get_user_connections(
    db: Session,
    current_user: User,
    status_filter: Optional[str] = None,
    role_filter: Optional[str] = None,
) -> List[ConnectionResponse]:
    """
    Retrieve all connections involving the current user (as requester or helper).
    """
    query = db.query(Connection)

    if role_filter == "requester":
        query = query.filter(Connection.requester_id == current_user.id)
    elif role_filter == "helper":
        query = query.filter(Connection.helper_id == current_user.id)
    else:
        query = query.filter(
            (Connection.requester_id == current_user.id) | (Connection.helper_id == current_user.id)
        )

    if status_filter:
        clean_status = status_filter.strip().upper()
        query = query.filter(Connection.status == clean_status)

    connections = query.order_by(Connection.updated_at.desc()).all()
    return [_hydrate_connection_response(db, c) for c in connections]


def get_connection_by_id(
    db: Session,
    connection_id: uuid.UUID,
    current_user: User,
) -> ConnectionResponse:
    """
    Retrieve a single connection by ID with authorization verification.
    """
    conn = db.query(Connection).filter(Connection.id == connection_id).first()
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found.",
        )

    if conn.requester_id != current_user.id and conn.helper_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this connection.",
        )

    return _hydrate_connection_response(db, conn)


def update_connection_status(
    db: Session,
    connection_id: uuid.UUID,
    current_user: User,
    action: str,
) -> ConnectionResponse:
    """
    Process connection lifecycle transitions:
    - Helper can ACCEPT or DECLINE a PENDING connection.
    - Requester can CANCEL an outgoing connection.
    - Unrelated users receive 403 Forbidden.
    """
    conn = db.query(Connection).filter(Connection.id == connection_id).first()
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found.",
        )

    clean_action = action.strip().lower()
    now = datetime.now(timezone.utc)

    if clean_action == "accept":
        if conn.helper_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the designated helper can accept this connection request.",
            )
        if conn.status == ConnectionStatus.ACCEPTED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Connection is already accepted.",
            )
        conn.status = ConnectionStatus.ACCEPTED.value
        conn.accepted_at = now
        conn.updated_at = now

    elif clean_action == "decline":
        if conn.helper_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the designated helper can decline this connection request.",
            )
        conn.status = ConnectionStatus.DECLINED.value
        conn.declined_at = now
        conn.updated_at = now

    elif clean_action == "cancel":
        if conn.requester_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the requester can cancel this connection request.",
            )
        conn.status = ConnectionStatus.CANCELLED.value
        conn.updated_at = now

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action '{action}'. Valid actions are 'accept', 'decline', 'cancel'.",
        )

    db.commit()
    db.refresh(conn)
    return _hydrate_connection_response(db, conn)
