import uuid
import logging
from enum import Enum
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.request import Request
from app.models.connection import Connection, ConnectionStatus
from app.models.safety import Block
from app.models.user import User

logger = logging.getLogger(__name__)


class RequestLifecycleStatus(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    EXPLORING = "EXPLORING"
    CONNECTED = "CONNECTED"
    RESOLUTION_PENDING = "RESOLUTION_PENDING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


def get_accepted_connection_for_request(
    db: Session, request_id: uuid.UUID, user_id: uuid.UUID
) -> Optional[Connection]:
    """
    Finds a legitimate accepted helper connection belonging to this request.
    Verifies that neither party has an active safety block against the other.
    """
    conn = (
        db.query(Connection)
        .filter(
            Connection.request_id == request_id,
            Connection.status.in_([ConnectionStatus.ACCEPTED.value, ConnectionStatus.COMPLETED.value]),
            (Connection.requester_id == user_id) | (Connection.helper_id == user_id),
        )
        .first()
    )
    if not conn:
        return None

    # Bidirectional safety block check
    active_block = (
        db.query(Block)
        .filter(
            ((Block.blocker_id == conn.requester_id) & (Block.blocked_id == conn.helper_id))
            | ((Block.blocker_id == conn.helper_id) & (Block.blocked_id == conn.requester_id))
        )
        .first()
    )
    if active_block:
        return None

    return conn


def validate_request_transition(
    db: Session,
    request: Request,
    target_status: str,
    user: User,
    is_independent_resolution: bool = False,
    resolution_note: Optional[str] = None,
) -> None:
    """
    Canonical authoritative validator for request lifecycle transitions.
    Rejects forged, invalid, or backwards transitions server-side.

    Lifecycle:
    UNRESOLVED -> EXPLORING -> CONNECTED -> RESOLUTION_PENDING -> RESOLVED

    Resolution Paths:
    - Path A (Helper Assisted): Requires accepted connection on this request.
    - Path B (Independent Resolution): Solved independently without fake connections.
    """
    # 1. User active authorization
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot modify request status.",
        )

    # 2. Requester ownership
    if request.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this request.",
        )

    curr = (request.status or "UNRESOLVED").upper()
    target = target_status.upper().strip()

    # Normalize synonym statuses if stored in existing DB
    if curr in ["OPEN", "PENDING"]:
        curr = "UNRESOLVED"
    if curr in ["MATCHED", "IN_PROGRESS"]:
        curr = "CONNECTED"
    if curr == "PARTIALLY_RESOLVED":
        curr = "EXPLORING"

    # Idempotent same-status
    if curr == target:
        return

    # 3. Terminal states: RESOLVED and CLOSED cannot be moved backwards
    if curr in ["RESOLVED", "CLOSED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Terminal status '{curr}' cannot be moved backwards to '{target}'.",
        )

    # Check for legitimate accepted connection
    accepted_conn = get_accepted_connection_for_request(db, request.id, user.id)

    # 4. State-specific transition rules
    if target == RequestLifecycleStatus.UNRESOLVED.value:
        if curr not in [RequestLifecycleStatus.UNRESOLVED.value, RequestLifecycleStatus.EXPLORING.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot revert from '{curr}' to 'UNRESOLVED'.",
            )

    elif target in [RequestLifecycleStatus.EXPLORING.value, "MATCHED"]:
        # Exploring/matched is valid when browsing helpers/resources before connection
        if curr not in [RequestLifecycleStatus.UNRESOLVED.value, RequestLifecycleStatus.EXPLORING.value, "MATCHED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition to '{target}' from '{curr}'.",
            )

    elif target == RequestLifecycleStatus.CONNECTED.value:
        # CRITICAL: CONNECTED is only allowed when an actual accepted helper connection exists!
        if not accepted_conn:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot set status to CONNECTED: no accepted helper connection exists for this request.",
            )

    elif target == RequestLifecycleStatus.RESOLUTION_PENDING.value:
        # Requires active accepted connection
        if not accepted_conn:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot set status to RESOLUTION_PENDING without an active accepted helper connection.",
            )

    elif target == RequestLifecycleStatus.RESOLVED.value:
        # PATH A: Helper Assisted (from CONNECTED or RESOLUTION_PENDING)
        if curr in [RequestLifecycleStatus.CONNECTED.value, RequestLifecycleStatus.RESOLUTION_PENDING.value]:
            if not accepted_conn:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot mark request as RESOLVED through helper assistance path without an accepted helper.",
                )
        # PATH B: Independent Resolution (from UNRESOLVED or EXPLORING)
        else:
            if is_independent_resolution is False and not accepted_conn:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot mark request as RESOLVED through helper assistance path without an accepted helper.",
                )

    elif target == RequestLifecycleStatus.CLOSED.value:
        # Cancellation allowed from any non-terminal state
        pass

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unrecognized request status '{target}'.",
        )
