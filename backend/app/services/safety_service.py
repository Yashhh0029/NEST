from datetime import datetime, timezone
import logging
from typing import List, Optional, Set
import uuid
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.community import CommunityAnswer, CommunityQuestion
from app.models.connection import Connection
from app.models.conversation import Conversation, Message
from app.models.safety import (
    Block,
    ModerationAction,
    ModerationActionType,
    Report,
    ReportStatus,
)
from app.models.user import User, UserRole
from app.schemas.safety import (
    BlockListResponse,
    BlockResponse,
    BlockUserSummary,
    ModerationActionListResponse,
    ModerationActionResponse,
    ModerationActionTypeEnum,
    ReportCreate,
    ReportDetailResponse,
    ReportListResponse,
    ReportReasonEnum,
    ReportStatusEnum,
    ReportUpdateStatus,
    ReportUserSummary,
)

logger = logging.getLogger(__name__)


# ============================================================================
# 1. Blocking Functions
# ============================================================================

def block_user(db: Session, blocker: User, target_user_id: uuid.UUID) -> BlockResponse:
    """
    Block a target user. Idempotent: returns existing block if already blocked.
    Rejects self-blocking and non-existent users.
    """
    if blocker.id == target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot block yourself.",
        )

    target_user = db.query(User).filter(User.id == target_user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    existing_block = (
        db.query(Block)
        .filter(Block.blocker_id == blocker.id, Block.blocked_id == target_user_id)
        .first()
    )
    if existing_block:
        return BlockResponse(
            id=existing_block.id,
            blocker_id=existing_block.blocker_id,
            blocked_id=existing_block.blocked_id,
            created_at=existing_block.created_at,
            blocked_user=BlockUserSummary(
                id=target_user.id,
                name=target_user.name,
                email=target_user.email,
            ),
        )

    now = datetime.now(timezone.utc)
    new_block = Block(
        id=uuid.uuid4(),
        blocker_id=blocker.id,
        blocked_id=target_user_id,
        created_at=now,
    )
    db.add(new_block)
    db.commit()
    db.refresh(new_block)

    # Phase 14: Cancel any active/future uncompleted sessions between blocker and blocked user
    from app.services.session_service import cancel_future_sessions_for_block
    cancel_future_sessions_for_block(db, blocker.id, target_user_id, blocker.id)

    return BlockResponse(
        id=new_block.id,
        blocker_id=new_block.blocker_id,
        blocked_id=new_block.blocked_id,
        created_at=new_block.created_at,
        blocked_user=BlockUserSummary(
            id=target_user.id,
            name=target_user.name,
            email=target_user.email,
        ),
    )


def unblock_user(db: Session, blocker: User, target_user_id: uuid.UUID) -> None:
    """
    Unblock a target user. Only removes blocker's own block record.
    """
    block_rec = (
        db.query(Block)
        .filter(Block.blocker_id == blocker.id, Block.blocked_id == target_user_id)
        .first()
    )
    if not block_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block record not found.",
        )

    db.delete(block_rec)
    db.commit()


def list_blocked_users(db: Session, user_id: uuid.UUID) -> BlockListResponse:
    """
    List all users blocked by the authenticated user.
    """
    blocks = (
        db.query(Block)
        .filter(Block.blocker_id == user_id)
        .order_by(Block.created_at.desc())
        .all()
    )

    items: List[BlockResponse] = []
    for b in blocks:
        target = db.query(User).filter(User.id == b.blocked_id).first()
        target_summary = (
            BlockUserSummary(id=target.id, name=target.name, email=target.email)
            if target
            else None
        )
        items.append(
            BlockResponse(
                id=b.id,
                blocker_id=b.blocker_id,
                blocked_id=b.blocked_id,
                created_at=b.created_at,
                blocked_user=target_summary,
            )
        )

    return BlockListResponse(total=len(items), blocks=items)


def is_blocked_bidirectional(db: Session, user_a_id: uuid.UUID, user_b_id: uuid.UUID) -> bool:
    """
    Check if either user has blocked the other.
    Returns True if user_a blocked user_b OR user_b blocked user_a.
    """
    if user_a_id == user_b_id:
        return False

    return (
        db.query(Block)
        .filter(
            or_(
                (Block.blocker_id == user_a_id) & (Block.blocked_id == user_b_id),
                (Block.blocker_id == user_b_id) & (Block.blocked_id == user_a_id),
            )
        )
        .first()
        is not None
    )


def get_blocked_user_ids(db: Session, user_id: uuid.UUID) -> Set[uuid.UUID]:
    """
    Get set of all user IDs where either user_id blocked them, or they blocked user_id.
    Used for efficient server-side filtering in People Matching.
    """
    blocks = (
        db.query(Block)
        .filter(or_(Block.blocker_id == user_id, Block.blocked_id == user_id))
        .all()
    )
    blocked_ids: Set[uuid.UUID] = set()
    for b in blocks:
        if b.blocker_id == user_id:
            blocked_ids.add(b.blocked_id)
        else:
            blocked_ids.add(b.blocker_id)
    return blocked_ids


# ============================================================================
# 2. Reporting Functions
# ============================================================================

def _hydrate_user_summary(user: Optional[User]) -> Optional[ReportUserSummary]:
    if not user:
        return None
    return ReportUserSummary(id=user.id, name=user.name, email=user.email)


def _hydrate_report_detail(db: Session, report: Report) -> ReportDetailResponse:
    reporter = db.query(User).filter(User.id == report.reporter_id).first()
    reported = db.query(User).filter(User.id == report.reported_user_id).first()
    resolver = (
        db.query(User).filter(User.id == report.resolved_by).first()
        if report.resolved_by
        else None
    )

    message_snippet = None
    if report.message_id:
        msg = db.query(Message).filter(Message.id == report.message_id).first()
        if msg:
            message_snippet = (
                msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            )

    connection_summary = None
    if report.connection_id:
        conn = db.query(Connection).filter(Connection.id == report.connection_id).first()
        if conn and conn.request:
            connection_summary = f"Request: {conn.request.raw_text[:60]}... Status: {conn.status}"

    question_title = None
    if report.question_id:
        q = db.query(CommunityQuestion).filter(CommunityQuestion.id == report.question_id).first()
        if q:
            question_title = q.title

    answer_snippet = None
    if report.answer_id:
        ans = db.query(CommunityAnswer).filter(CommunityAnswer.id == report.answer_id).first()
        if ans:
            answer_snippet = ans.body[:100] + "..." if len(ans.body) > 100 else ans.body

    return ReportDetailResponse(
        id=report.id,
        reporter_id=report.reporter_id,
        reported_user_id=report.reported_user_id,
        connection_id=report.connection_id,
        message_id=report.message_id,
        question_id=report.question_id,
        answer_id=report.answer_id,
        reason=ReportReasonEnum(report.reason),
        description=report.description,
        status=ReportStatusEnum(report.status),
        created_at=report.created_at,
        resolved_at=report.resolved_at,
        resolution_note=report.resolution_note,
        reporter=_hydrate_user_summary(reporter),
        reported_user=_hydrate_user_summary(reported),
        resolved_by_user=_hydrate_user_summary(resolver),
        message_snippet=message_snippet,
        connection_summary=connection_summary,
        question_title=question_title,
        answer_snippet=answer_snippet,
    )


def create_report(db: Session, reporter: User, payload: ReportCreate) -> ReportDetailResponse:
    """
    Submit a report against a user, message, or community content.
    Validates reporter != reported user, reported user exists,
    and reporter is authorized for any message_id/connection_id supplied.
    Throttles duplicate active reports for the same incident.
    """
    if reporter.id == payload.reported_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot report yourself.",
        )

    reported_user = db.query(User).filter(User.id == payload.reported_user_id).first()
    if not reported_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reported user not found.",
        )

    # Validate connection authorization if supplied
    if payload.connection_id:
        conn = db.query(Connection).filter(Connection.id == payload.connection_id).first()
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connection record not found.",
            )
        if conn.requester_id != reporter.id and conn.helper_id != reporter.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot report an interaction in which you were not a participant.",
            )

    # Validate message authorization if supplied (prevents private message leakage)
    if payload.message_id:
        msg = db.query(Message).filter(Message.id == payload.message_id).first()
        if not msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message record not found.",
            )
        conv = (
            db.query(Conversation)
            .filter(Conversation.id == msg.conversation_id)
            .first()
        )
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )
        conn = db.query(Connection).filter(Connection.id == conv.connection_id).first()
        if not conn or (conn.requester_id != reporter.id and conn.helper_id != reporter.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot report a message from a conversation you were not part of.",
            )
        if not payload.connection_id:
            payload.connection_id = conn.id

    # Validate question if supplied (and no answer_id)
    if payload.question_id and not payload.answer_id:
        q = db.query(CommunityQuestion).filter(CommunityQuestion.id == payload.question_id).first()
        if not q:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Community question not found.",
            )
        if payload.reported_user_id != q.author_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reported user does not match question author.",
            )

    # Validate answer if supplied
    if payload.answer_id:
        ans = db.query(CommunityAnswer).filter(CommunityAnswer.id == payload.answer_id).first()
        if not ans:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Community answer not found.",
            )
        if payload.reported_user_id != ans.author_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reported user does not match answer author.",
            )
        if not payload.question_id:
            payload.question_id = ans.question_id

    # Anti-spam: check for existing active duplicate report
    dup_query = db.query(Report).filter(
        Report.reporter_id == reporter.id,
        Report.reported_user_id == payload.reported_user_id,
        Report.reason == payload.reason.value,
        Report.status.in_([ReportStatus.OPEN.value, ReportStatus.UNDER_REVIEW.value]),
    )
    if payload.message_id:
        dup_query = dup_query.filter(Report.message_id == payload.message_id)
    if payload.question_id:
        dup_query = dup_query.filter(Report.question_id == payload.question_id)
    if payload.answer_id:
        dup_query = dup_query.filter(Report.answer_id == payload.answer_id)

    if dup_query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active report for this user and reason under investigation.",
        )

    now = datetime.now(timezone.utc)
    report = Report(
        id=uuid.uuid4(),
        reporter_id=reporter.id,
        reported_user_id=payload.reported_user_id,
        connection_id=payload.connection_id,
        message_id=payload.message_id,
        question_id=payload.question_id,
        answer_id=payload.answer_id,
        reason=payload.reason.value,
        description=payload.description.strip() if payload.description else None,
        status=ReportStatus.OPEN.value,
        created_at=now,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return _hydrate_report_detail(db, report)


def get_user_reports(db: Session, user_id: uuid.UUID) -> ReportListResponse:
    """
    Retrieve all reports submitted by the authenticated user.
    """
    reports = (
        db.query(Report)
        .filter(Report.reporter_id == user_id)
        .order_by(Report.created_at.desc())
        .all()
    )
    return ReportListResponse(
        total=len(reports),
        reports=[_hydrate_report_detail(db, r) for r in reports],
    )


def get_report_by_id(db: Session, report_id: uuid.UUID, current_user: User) -> ReportDetailResponse:
    """
    Get report details. Accessible only to the reporter or an administrator.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    if current_user.role != UserRole.ADMIN and report.reporter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this report.",
        )

    return _hydrate_report_detail(db, report)


# ============================================================================
# 3. Admin Moderation & Audit Logging Functions
# ============================================================================

def admin_list_reports(
    db: Session,
    status_filter: Optional[ReportStatusEnum] = None,
    page: int = 1,
    limit: int = 50,
) -> ReportListResponse:
    """
    Admin listing of all reports with optional status filtering.
    """
    query = db.query(Report)
    if status_filter:
        query = query.filter(Report.status == status_filter.value)

    total = query.count()
    offset = (max(1, page) - 1) * limit
    reports = query.order_by(Report.created_at.desc()).offset(offset).limit(limit).all()

    return ReportListResponse(
        total=total,
        reports=[_hydrate_report_detail(db, r) for r in reports],
    )


def admin_get_report_detail(db: Session, report_id: uuid.UUID) -> ReportDetailResponse:
    """
    Admin detailed inspection of a single report.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )
    return _hydrate_report_detail(db, report)


def admin_update_report(
    db: Session,
    admin: User,
    report_id: uuid.UUID,
    payload: ReportUpdateStatus,
) -> ReportDetailResponse:
    """
    Admin status update on a report (UNDER_REVIEW, RESOLVED, DISMISSED).
    Logs an immutable moderation audit record.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )

    old_status = report.status
    report.status = payload.status.value
    now = datetime.now(timezone.utc)

    if payload.status in [ReportStatusEnum.RESOLVED, ReportStatusEnum.DISMISSED]:
        report.resolved_at = now
        report.resolved_by = admin.id
        report.resolution_note = payload.resolution_note

    # Determine action type for audit log
    if payload.status == ReportStatusEnum.RESOLVED:
        action_type = ModerationActionType.REPORT_RESOLVED
    elif payload.status == ReportStatusEnum.DISMISSED:
        action_type = ModerationActionType.REPORT_DISMISSED
    else:
        action_type = ModerationActionType.REPORT_REVIEWED

    audit_entry = ModerationAction(
        id=uuid.uuid4(),
        admin_id=admin.id,
        target_user_id=report.reported_user_id,
        report_id=report.id,
        action=action_type,
        reason=payload.resolution_note or f"Report status changed from {old_status} to {payload.status.value}",
        metadata_json={
            "previous_status": old_status,
            "new_status": payload.status.value,
        },
        created_at=now,
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(report)

    return _hydrate_report_detail(db, report)


def admin_suspend_user(
    db: Session,
    admin: User,
    target_user_id: uuid.UUID,
    reason: str,
) -> None:
    """
    Suspend a user account (is_active = False).
    Reuses existing is_active model. Prevents all normal authenticated actions.
    Preserves historical records. Logs immutable moderation action.
    """
    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found.",
        )

    if target.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrator accounts cannot be suspended via standard moderation.",
        )

    target.is_active = False
    now = datetime.now(timezone.utc)

    audit_entry = ModerationAction(
        id=uuid.uuid4(),
        admin_id=admin.id,
        target_user_id=target.id,
        report_id=None,
        action=ModerationActionType.USER_SUSPENDED,
        reason=reason,
        metadata_json={
            "target_user_email": target.email,
            "target_user_name": target.name,
            "action": "deactivated",
        },
        created_at=now,
    )
    db.add(audit_entry)
    db.commit()

    # Phase 14: Cancel any active/future uncompleted sessions for suspended user
    from app.services.session_service import cancel_future_sessions_for_suspension
    cancel_future_sessions_for_suspension(db, target.id)


def admin_reactivate_user(
    db: Session,
    admin: User,
    target_user_id: uuid.UUID,
    reason: str,
) -> None:
    """
    Reactivate a suspended user account (is_active = True).
    Restores normal authenticated actions. Logs immutable moderation action.
    """
    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found.",
        )

    target.is_active = True
    now = datetime.now(timezone.utc)

    audit_entry = ModerationAction(
        id=uuid.uuid4(),
        admin_id=admin.id,
        target_user_id=target.id,
        report_id=None,
        action=ModerationActionType.USER_REACTIVATED,
        reason=reason,
        metadata_json={
            "target_user_email": target.email,
            "target_user_name": target.name,
            "action": "reactivated",
        },
        created_at=now,
    )
    db.add(audit_entry)
    db.commit()


def admin_list_audit_logs(
    db: Session,
    page: int = 1,
    limit: int = 50,
) -> ModerationActionListResponse:
    """
    List all moderation audit actions with pagination.
    """
    total = db.query(ModerationAction).count()
    offset = (max(1, page) - 1) * limit
    logs = (
        db.query(ModerationAction)
        .order_by(ModerationAction.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items: List[ModerationActionResponse] = []
    for l in logs:
        admin_user = db.query(User).filter(User.id == l.admin_id).first()
        target_user = (
            db.query(User).filter(User.id == l.target_user_id).first()
            if l.target_user_id
            else None
        )
        items.append(
            ModerationActionResponse(
                id=l.id,
                admin_id=l.admin_id,
                target_user_id=l.target_user_id,
                report_id=l.report_id,
                action=ModerationActionTypeEnum(l.action),
                reason=l.reason,
                metadata_json=l.metadata_json,
                created_at=l.created_at,
                admin_name=admin_user.name if admin_user else None,
                target_user_name=target_user.name if target_user else None,
            )
        )

    return ModerationActionListResponse(total=total, actions=items)


def is_connection_safety_restricted(db: Session, connection_id: uuid.UUID) -> bool:
    """
    Check if a connection is restricted due to a safety/moderation action
    (e.g., active unresolved reports or moderation actions associated with this connection).
    """
    # 1. Unresolved reports targeting this connection
    active_report = (
        db.query(Report)
        .filter(
            Report.connection_id == connection_id,
            Report.status.in_([ReportStatus.OPEN.value, ReportStatus.UNDER_REVIEW.value]),
        )
        .first()
    )
    if active_report:
        return True

    # 2. Moderation actions on reports linked to this connection that resulted in resolution/action
    resolved_action = (
        db.query(ModerationAction)
        .join(Report, ModerationAction.report_id == Report.id)
        .filter(
            Report.connection_id == connection_id,
            ModerationAction.action.in_([
                ModerationActionType.REPORT_RESOLVED,
                ModerationActionType.USER_SUSPENDED,
            ]),
        )
        .first()
    )
    if resolved_action:
        return True

    return False
