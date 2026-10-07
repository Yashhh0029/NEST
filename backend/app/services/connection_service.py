import logging
from datetime import datetime, timezone
from typing import List, Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
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
from app.services.safety_service import (
    is_blocked_bidirectional,
    is_connection_safety_restricted,
)
from app.services.notification_service import is_user_actively_online
from app.services.email_service import dispatch_email_async, render_connection_event_email

logger = logging.getLogger(__name__)



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
        completed_at=conn.completed_at,
        requester=requester_summary,
        helper=helper_summary,
        request=request_summary,
    )


def _maybe_send_connection_request_email(current_user: User, helper: User, conn: Connection) -> None:
    try:
        if not helper.email:
            return
        if not getattr(helper, "is_active", True):
            return
        if is_user_actively_online(helper.id):
            logger.info("Helper %s is actively online; skipping connection request email", helper.id)
            return

        requester_name = current_user.name or (current_user.email.split("@")[0].capitalize() if current_user.email else "A NEST member")
        helper_name = helper.name or (helper.email.split("@")[0].capitalize() if helper.email else "Neighbor")
        action_url = f"{settings.FRONTEND_URL}/dashboard"
        event_title = "New Connection Request"
        event_message = f"{requester_name} sent you a connection request on NEST regarding their request. Visit your dashboard to view the message and respond."
        html_body, text_body = render_connection_event_email(
            recipient_name=helper_name,
            event_title=event_title,
            event_message=event_message,
            action_url=action_url,
            action_label="View Connection Request",
        )
        updated_stamp = conn.updated_at.isoformat() if conn.updated_at else "init"
        idempotency_key = f"conn_req_{conn.id}_{updated_stamp}"
        dispatch_email_async(
            to_email=helper.email,
            recipient_id=helper.id,
            notification_type="connection_requested",
            subject=f"New connection request from {requester_name} — NEST",
            html_body=html_body,
            text_body=text_body,
            idempotency_key=idempotency_key,
            metadata_payload={"connection_id": str(conn.id), "requester_id": str(current_user.id)},
        )
    except Exception as exc:
        logger.warning("Failed to dispatch connection request email asynchronously: %s", exc)


def _maybe_send_connection_accepted_email(helper_user: User, requester: User, conn: Connection) -> None:
    try:
        if not requester.email:
            return
        if not getattr(requester, "is_active", True):
            return
        if is_user_actively_online(requester.id):
            logger.info("Requester %s is actively online; skipping connection accepted email", requester.id)
            return

        helper_name = helper_user.name or (helper_user.email.split("@")[0].capitalize() if helper_user.email else "A helper")
        requester_name = requester.name or (requester.email.split("@")[0].capitalize() if requester.email else "Neighbor")
        action_url = f"{settings.FRONTEND_URL}/chat"
        event_title = "Connection Request Accepted"
        event_message = f"{helper_name} accepted your connection request on NEST! You can now chat and coordinate directly."
        html_body, text_body = render_connection_event_email(
            recipient_name=requester_name,
            event_title=event_title,
            event_message=event_message,
            action_url=action_url,
            action_label="Open Chat",
        )
        accepted_stamp = conn.accepted_at.isoformat() if conn.accepted_at else "init"
        idempotency_key = f"conn_acc_{conn.id}_{accepted_stamp}"
        dispatch_email_async(
            to_email=requester.email,
            recipient_id=requester.id,
            notification_type="connection_accepted",
            subject=f"{helper_name} accepted your connection request — NEST",
            html_body=html_body,
            text_body=text_body,
            idempotency_key=idempotency_key,
            metadata_payload={"connection_id": str(conn.id), "helper_id": str(helper_user.id)},
        )
    except Exception as exc:
        logger.warning("Failed to dispatch connection accepted email asynchronously: %s", exc)


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

    # 4. Check block relationship
    if is_blocked_bidirectional(db, current_user.id, payload.helper_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Action not permitted due to safety restrictions.",
        )

    # 5. Check for existing connection between this requester, helper, and request
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
        _maybe_send_connection_request_email(current_user, helper, existing_conn)
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
    _maybe_send_connection_request_email(current_user, helper, new_conn)

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

    if clean_action == "reactivate":
        if conn.requester_id != current_user.id and conn.helper_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only participants in this connection can reactivate it.",
            )
        if conn.status != ConnectionStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only completed connections can be reactivated. Current status: '{conn.status}'.",
            )
        # Safety rules:
        # 1. Blocked check
        if is_blocked_bidirectional(db, conn.requester_id, conn.helper_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Action not permitted due to safety restrictions.",
            )
        # 2. Safety / moderation restriction check
        if is_connection_safety_restricted(db, conn.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This conversation cannot be reactivated due to active safety/moderation restrictions.",
            )
        # 3. User active / not suspended check
        other_user_id = conn.helper_id if current_user.id == conn.requester_id else conn.requester_id
        other_user = db.query(User).filter(User.id == other_user_id).first()
        if not current_user.is_active or (other_user and not other_user.is_active):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot reactivate conversation because an account is suspended or deactivated.",
            )

        conn.status = ConnectionStatus.ACCEPTED.value
        conn.updated_at = now
        db.commit()
        db.refresh(conn)
        return _hydrate_connection_response(db, conn)

    if conn.status == ConnectionStatus.COMPLETED.value:
        if clean_action == "complete":
            return _hydrate_connection_response(db, conn)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Completed connections cannot be modified.",
        )

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
        if conn.status != ConnectionStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot accept connection with status '{conn.status}'. Only pending connections can be accepted.",
            )
        conn.status = ConnectionStatus.ACCEPTED.value
        conn.accepted_at = now
        conn.updated_at = now

        # Legitimate lifecycle transition: linked request transitions to CONNECTED
        if conn.request_id:
            req = db.query(Request).filter(Request.id == conn.request_id).first()
            if req and req.status in ["UNRESOLVED", "EXPLORING", "OPEN", "PENDING"]:
                req.status = "CONNECTED"
                req.updated_at = now

    elif clean_action == "decline":
        if conn.helper_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the designated helper can decline this connection request.",
            )
        if conn.status != ConnectionStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot decline connection with status '{conn.status}'. Only pending connections can be declined.",
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
        if conn.status != ConnectionStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel connection with status '{conn.status}'. Only pending connections can be cancelled.",
            )
        conn.status = ConnectionStatus.CANCELLED.value
        conn.updated_at = now

    elif clean_action == "complete":
        if conn.requester_id != current_user.id and conn.helper_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only participants in this connection can mark it as completed.",
            )
        if conn.status != ConnectionStatus.ACCEPTED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only accepted connections can be completed. Current status: {conn.status}.",
            )
        conn.status = ConnectionStatus.COMPLETED.value
        conn.completed_at = now
        conn.updated_at = now

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action '{action}'. Valid actions are 'accept', 'decline', 'cancel', 'complete', 'reactivate'.",
        )

    db.commit()
    db.refresh(conn)
    if clean_action == "accept" and conn.requester:
        _maybe_send_connection_accepted_email(current_user, conn.requester, conn)
    return _hydrate_connection_response(db, conn)
