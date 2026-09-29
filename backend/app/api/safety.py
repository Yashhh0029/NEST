from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_admin_user, get_current_user, get_db
from app.models.user import User
from app.schemas.safety import (
    BlockListResponse,
    BlockResponse,
    ModerationActionListResponse,
    ReportCreate,
    ReportDetailResponse,
    ReportListResponse,
    ReportStatusEnum,
    ReportUpdateStatus,
    UserSuspensionRequest,
)
from app.services import safety_service

router = APIRouter(tags=["Safety & Moderation"])


# ============================================================================
# 1. Blocking Endpoints
# ============================================================================

@router.post(
    "/blocks/{user_id}",
    response_model=BlockResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Block a target user",
    description="Blocks user bidirectionally preventing new connections, chat, and matching.",
)
def block_user_endpoint(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BlockResponse:
    return safety_service.block_user(db, current_user, user_id)


@router.delete(
    "/blocks/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unblock a user",
    description="Removes authenticated user's block on target user.",
)
def unblock_user_endpoint(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    safety_service.unblock_user(db, current_user, user_id)


@router.get(
    "/blocks",
    response_model=BlockListResponse,
    status_code=status.HTTP_200_OK,
    summary="List blocked users",
    description="Lists all users blocked by the authenticated user.",
)
def list_blocks_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BlockListResponse:
    return safety_service.list_blocked_users(db, current_user.id)


# ============================================================================
# 2. Reporting Endpoints (User-Facing)
# ============================================================================

@router.post(
    "/reports",
    response_model=ReportDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a report against a user or message",
    description="Creates a safety report with reason, description, and target validation.",
)
def create_report_endpoint(
    payload: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportDetailResponse:
    return safety_service.create_report(db, current_user, payload)


@router.get(
    "/reports/mine",
    response_model=ReportListResponse,
    status_code=status.HTTP_200_OK,
    summary="List reports submitted by current user",
    description="Retrieves history of reports submitted by the authenticated user.",
)
def get_my_reports_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    return safety_service.get_user_reports(db, current_user.id)


@router.get(
    "/reports/{report_id}",
    response_model=ReportDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="View report detail",
    description="Accessible only to the reporter or an administrator.",
)
def get_report_endpoint(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportDetailResponse:
    return safety_service.get_report_by_id(db, report_id, current_user)


# ============================================================================
# 3. Admin Moderation & Audit Endpoints (Strictly Admin-Only)
# ============================================================================

@router.get(
    "/admin/reports",
    response_model=ReportListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all reports for moderation (Admin only)",
)
def admin_list_reports_endpoint(
    status_filter: Optional[ReportStatusEnum] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    return safety_service.admin_list_reports(db, status_filter, page, limit)


@router.get(
    "/admin/reports/{report_id}",
    response_model=ReportDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single report detail for moderation (Admin only)",
)
def admin_get_report_endpoint(
    report_id: uuid.UUID,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> ReportDetailResponse:
    return safety_service.admin_get_report_detail(db, report_id)


@router.patch(
    "/admin/reports/{report_id}",
    response_model=ReportDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update report status & resolve/dismiss (Admin only)",
)
def admin_update_report_endpoint(
    report_id: uuid.UUID,
    payload: ReportUpdateStatus,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> ReportDetailResponse:
    return safety_service.admin_update_report(db, admin, report_id, payload)


@router.post(
    "/admin/users/{user_id}/suspend",
    status_code=status.HTTP_200_OK,
    summary="Suspend user account (Admin only)",
)
def admin_suspend_user_endpoint(
    user_id: uuid.UUID,
    payload: UserSuspensionRequest,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    safety_service.admin_suspend_user(db, admin, user_id, payload.reason)
    return {"detail": "User account suspended successfully."}


@router.post(
    "/admin/users/{user_id}/reactivate",
    status_code=status.HTTP_200_OK,
    summary="Reactivate user account (Admin only)",
)
def admin_reactivate_user_endpoint(
    user_id: uuid.UUID,
    payload: UserSuspensionRequest,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    safety_service.admin_reactivate_user(db, admin, user_id, payload.reason)
    return {"detail": "User account reactivated successfully."}


@router.get(
    "/admin/audit-logs",
    response_model=ModerationActionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List moderation audit log entries (Admin only)",
)
def admin_list_audit_logs_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> ModerationActionListResponse:
    return safety_service.admin_list_audit_logs(db, page, limit)
