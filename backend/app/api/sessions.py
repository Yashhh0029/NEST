import logging
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.session import (
    AssistanceSessionResponse,
    SessionActionPayload,
    SessionCreatePayload,
    SessionListResponse,
    SessionReschedulePayload,
)
from app.services import session_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


async def _safe_broadcast_session_event(
    db: Session,
    session_resp: AssistanceSessionResponse,
    event_type: str,
):
    try:
        from app.api.ws_chat import manager
        conv = (
            db.query(Conversation)
            .filter(Conversation.connection_id == session_resp.connection_id)
            .first()
        )
        if conv:
            await manager.broadcast(
                conv.id,
                {
                    "type": f"SESSION_{event_type}",
                    "session_id": str(session_resp.id),
                    "connection_id": str(session_resp.connection_id),
                    "status": session_resp.status,
                    "title": session_resp.title,
                    "scheduled_start": session_resp.scheduled_start.isoformat(),
                    "scheduled_end": session_resp.scheduled_end.isoformat(),
                    "modality": session_resp.modality,
                    "meeting_place_name": session_resp.meeting_place_name,
                    "meeting_url": session_resp.meeting_url,
                },
            )
    except Exception as exc:
        logger.warning(f"Session WebSocket broadcast failed gracefully: {exc}")


@router.post("", response_model=AssistanceSessionResponse, status_code=status.HTTP_201_CREATED)
async def propose_session(
    payload: SessionCreatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Propose an assistance session with an accepted connection partner.
    Requires server-side venue validation (IN_PERSON) or HTTPS URL (REMOTE).
    """
    res = session_service.propose_session(current_user, payload, db)
    await _safe_broadcast_session_event(db, res, "PROPOSED")
    return res


@router.get("", response_model=SessionListResponse)
def list_sessions(
    status: Optional[str] = Query(None, description="Optional status filter (e.g. PROPOSED, CONFIRMED, COMPLETED)"),
    request_id: Optional[uuid.UUID] = Query(None, description="Filter sessions for a specific request"),
    connection_id: Optional[uuid.UUID] = Query(None, description="Filter sessions for a specific connection"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List assistance sessions involving the authenticated user.
    """
    return session_service.list_user_sessions(current_user, status, request_id, connection_id, db)


@router.get("/{session_id}", response_model=AssistanceSessionResponse)
def get_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve single session details. IDOR protected: only session participants can access.
    """
    return session_service.get_session_by_id(session_id, current_user, db)


@router.post("/{session_id}/accept", response_model=AssistanceSessionResponse)
async def accept_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Accept a proposed session or reschedule proposal. Only recipient can accept.
    Anti-self-accept strictly enforced.
    """
    res = session_service.accept_session(session_id, current_user, db)
    await _safe_broadcast_session_event(db, res, "CONFIRMED")
    return res


@router.post("/{session_id}/decline", response_model=AssistanceSessionResponse)
async def decline_session(
    session_id: uuid.UUID,
    payload: SessionActionPayload = SessionActionPayload(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Decline a proposed session or reschedule proposal. Only recipient can decline.
    """
    res = session_service.decline_session(session_id, current_user, payload, db)
    await _safe_broadcast_session_event(db, res, "DECLINED")
    return res


@router.post("/{session_id}/cancel", response_model=AssistanceSessionResponse)
async def cancel_session(
    session_id: uuid.UUID,
    payload: SessionActionPayload = SessionActionPayload(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel an assistance session. Either participant can cancel.
    """
    res = session_service.cancel_session(session_id, current_user, payload, db)
    await _safe_broadcast_session_event(db, res, "CANCELLED")
    return res


@router.post("/{session_id}/reschedule", response_model=AssistanceSessionResponse)
async def reschedule_session(
    session_id: uuid.UUID,
    payload: SessionReschedulePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Propose rescheduling an assistance session. Flips proposer and recipient
    so the other participant can review and accept.
    """
    res = session_service.reschedule_session(session_id, current_user, payload, db)
    await _safe_broadcast_session_event(db, res, "RESCHEDULE_PROPOSED")
    return res


@router.post("/{session_id}/complete", response_model=AssistanceSessionResponse)
async def complete_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dual-confirmation session completion. Transitions to COMPLETED once both
    requester and helper confirm.
    """
    res = session_service.complete_session(session_id, current_user, db)
    if res.status == "COMPLETED":
        await _safe_broadcast_session_event(db, res, "COMPLETED")
    return res


@router.get("/{session_id}/ics")
@router.get("/{session_id}/calendar.ics")
def export_session_calendar(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export RFC 5545 standard .ics calendar file for the assistance session.
    """
    ics_content = session_service.generate_session_ics(session_id, current_user, db)
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f"attachment; filename=nest-session-{session_id}.ics",
            "Cache-Control": "no-cache",
        },
    )
