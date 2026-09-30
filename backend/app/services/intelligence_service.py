from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.community import CommunityQuestion
from app.models.connection import Connection, ConnectionStatus
from app.models.request import Request, RequestSavedResource
from app.models.review import Review
from app.models.session import AssistanceSession, SessionStatus
from app.models.user import User
from app.schemas.community import CommunitySearchItem
from app.schemas.intelligence import (
    ActiveConnectionSummary,
    NeedIntelligenceBundle,
    NeedProgressItem,
    NeedProgressUpdate,
    NeedStatusEnum,
    RequestIntelligenceResponse,
    RequestResolvePayload,
    ResolutionSourceEnum,
    SavedResourceCreate,
    SavedResourceResponse,
)
from app.schemas.matching import HelperCandidate
from app.schemas.resource import ResourceItem
from app.services import community_service, matching_service, resource_service
from app.services.resource_service import resolve_category_from_need
from app.services.safety_service import get_blocked_user_ids

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def _normalize_need_key(category: str) -> str:
    return category.strip().lower().replace(" ", "_")


def _get_active_connections_summary(db: Session, request_id: uuid.UUID) -> List[ActiveConnectionSummary]:
    conns = (
        db.query(Connection)
        .filter(Connection.request_id == request_id)
        .order_by(Connection.created_at.desc())
        .all()
    )
    items: List[ActiveConnectionSummary] = []
    for c in conns:
        helper = db.query(User).filter(User.id == c.helper_id).first()
        has_rev = (
            db.query(Review)
            .filter(Review.connection_id == c.id)
            .first()
            is not None
        )
        items.append(
            ActiveConnectionSummary(
                id=c.id,
                helper_id=c.helper_id,
                helper_name=helper.name if helper else "Community Helper",
                status=c.status,
                created_at=c.created_at,
                completed_at=c.completed_at,
                has_review=has_rev,
            )
        )
    return items


def _generate_action_plan(
    needs: List[NeedIntelligenceBundle],
    active_conns: List[ActiveConnectionSummary],
    city: Optional[str],
    area: Optional[str],
) -> List[str]:
    """
    Deterministic synthesis of immediate recommended next steps.
    Derived strictly from verified retrieved data (zero hallucinated entities).
    """
    steps: List[str] = []
    loc_label = f" in {area}" if area else (f" in {city}" if city else "")

    # 1. Connection-driven actions
    accepted_conns = [c for c in active_conns if c.status == ConnectionStatus.ACCEPTED.value]
    completed_without_review = [c for c in active_conns if c.status == ConnectionStatus.COMPLETED.value and not c.has_review]

    if completed_without_review:
        steps.append(f"Leave a factual review for {completed_without_review[0].helper_name} to update community reputation.")
    elif accepted_conns:
        steps.append(f"Message {accepted_conns[0].helper_name} regarding your open requirements{loc_label}.")

    # 2. Need-driven actions
    for bundle in needs:
        if bundle.status == NeedStatusEnum.UNRESOLVED or bundle.status == NeedStatusEnum.EXPLORING:
            if bundle.matched_helpers:
                best_helper = bundle.matched_helpers[0]
                steps.append(f"Connect with verified helper {best_helper.name} for {bundle.item}{loc_label}.")
                break
            elif bundle.community_questions:
                best_q = bundle.community_questions[0].question
                steps.append(f"Read community guide '{best_q.title}' for practical local tips.")
                break
            elif bundle.local_resources:
                best_res = bundle.local_resources[0]
                steps.append(f"Explore {best_res.name} ({bundle.category}) located {best_res.distance_km or 'nearby'} km away.")
                break

    # 3. Fallback or general completion step
    if not steps:
        if all(b.status == NeedStatusEnum.RESOLVED for b in needs) and needs:
            steps.append("All extracted needs are resolved! Mark your overall request as resolved.")
        else:
            steps.append(f"Explore community recommendations or connect with local helpers{loc_label}.")

    return steps[:3]


# ============================================================================
# Core Intelligence Service
# ============================================================================

def get_request_intelligence(
    db: Session,
    request_id: uuid.UUID,
    current_user: User,
) -> RequestIntelligenceResponse:
    """
    Aggregates People, Community, Resources, and Connections into a unified,
    need-centric intelligence bundle for the authenticated request owner.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot access request intelligence.",
        )

    req = db.query(Request).filter(Request.id == request_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found.",
        )

    # Strict ownership / IDOR check
    if req.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access intelligence for this request.",
        )

    # 1. Parse or retrieve extracted needs
    extracted_needs = []
    if req.extracted_requirements and isinstance(req.extracted_requirements, dict):
        extracted_needs = req.extracted_requirements.get("needs", [])

    if not extracted_needs:
        extracted_needs = [{"category": "general", "item": "General newcomer assistance"}]

    # 2. Need progress map
    progress_map = dict(req.need_progress or {})

    # 3. Retrieve all candidate helpers once via existing Phase 5 matching engine
    blocked_ids = get_blocked_user_ids(db, current_user.id)
    all_matched_helpers: List[HelperCandidate] = []
    try:
        matching_result = matching_service.match_request_to_helpers(
            db=db,
            requesting_user=current_user,
            request_id=req.id,
            limit=10,
        )
        all_matched_helpers = [
            h for h in matching_result.matches
            if h.user_id not in blocked_ids
        ]
    except Exception as exc:
        logger.warning(f"Helper matching fallback for request {req.id}: {exc}")

    # 4. Active connections
    active_conns = _get_active_connections_summary(db, req.id)

    # 5. Saved resources
    saved_res_records = (
        db.query(RequestSavedResource)
        .filter(RequestSavedResource.request_id == req.id)
        .order_by(RequestSavedResource.created_at.desc())
        .all()
    )
    saved_resources_resp = [
        SavedResourceResponse.model_validate(r) for r in saved_res_records
    ]

    # 6. Deduplicate Google Places searches across needs sharing the same category/locality
    resource_cache_by_category: Dict[str, List[ResourceItem]] = {}

    needs_bundles: List[NeedIntelligenceBundle] = []
    for need_dict in extracted_needs:
        cat_raw = need_dict.get("category", "general")
        item_text = need_dict.get("item", cat_raw)
        norm_key = _normalize_need_key(cat_raw)

        # Current progress status
        prog_entry = progress_map.get(norm_key, {})
        need_status_str = prog_entry.get("status", NeedStatusEnum.UNRESOLVED.value)
        try:
            need_status = NeedStatusEnum(need_status_str)
        except ValueError:
            need_status = NeedStatusEnum.UNRESOLVED

        resolved_via = prog_entry.get("resolved_via")
        resolved_entity_id = prog_entry.get("resolved_entity_id")

        # 6a. Filter People candidates relevant to this need
        # Match candidates whose skills or bio relate to this category
        relevant_helpers: List[HelperCandidate] = []
        cat_clean = cat_raw.lower()
        for h in all_matched_helpers:
            relevance = False
            for s in h.matched_skills:
                if any(k in s.lower() for k in [cat_clean, item_text.lower()]):
                    relevance = True
                    break
            if relevance or len(relevant_helpers) < 2:
                relevant_helpers.append(h)
            if len(relevant_helpers) >= 3:
                break

        # 6b. Retrieve Community Questions via Phase 12 semantic search
        comm_results: List[CommunitySearchItem] = []
        try:
            query_q = f"{item_text} {req.city or ''} {req.area or ''}".strip()
            comm_resp = community_service.search_community(
                db=db,
                query_text=query_q,
                current_user=current_user,
                city=req.city,
                area=req.area,
                limit=3,
            )
            comm_results = comm_resp.results[:3]
        except Exception as exc:
            logger.warning(f"Community search fallback for need {norm_key}: {exc}")

        # 6c. Retrieve Local Places via Phase 10 Google Places (with category deduplication)
        cat_slug = resolve_category_from_need(cat_raw) or "accommodation"
        if cat_slug not in resource_cache_by_category:
            try:
                res_resp = resource_service.search_resources_for_request(
                    db=db,
                    current_user=current_user,
                    request_id=req.id,
                    category=cat_slug,
                    limit=3,
                )
                resource_cache_by_category[cat_slug] = res_resp.resources[:3]
            except Exception as exc:
                logger.warning(f"Resource search fallback for need {cat_slug}: {exc}")
                resource_cache_by_category[cat_slug] = []

        local_places = resource_cache_by_category.get(cat_slug, [])

        needs_bundles.append(
            NeedIntelligenceBundle(
                category=cat_raw,
                item=item_text,
                status=need_status,
                resolved_via=resolved_via,
                resolved_entity_id=resolved_entity_id,
                matched_helpers=relevant_helpers[:3],
                community_questions=comm_results,
                local_resources=local_places,
            )
        )

    # 7. Progress & State calculations (Mandatory Adjustments 3 & 5)
    total_needs = len(needs_bundles)
    resolved_count = sum(1 for b in needs_bundles if b.status == NeedStatusEnum.RESOLVED)
    progress_pct = round((resolved_count / total_needs) * 100.0, 1) if total_needs > 0 else 0.0

    # Auto-update request lifecycle state if not terminal CLOSED or manual RESOLVED
    if req.status not in ["RESOLVED", "CLOSED"]:
        has_accepted_conn = any(c.status == ConnectionStatus.ACCEPTED.value for c in active_conns)
        if resolved_count == total_needs and total_needs > 0:
            req.status = "RESOLVED"
            if not req.resolved_at:
                req.resolved_at = datetime.now(timezone.utc)
        elif resolved_count > 0:
            req.status = "PARTIALLY_RESOLVED"
        elif has_accepted_conn:
            req.status = "IN_PROGRESS"
        db.commit()

    action_plan = _generate_action_plan(needs_bundles, active_conns, req.city, req.area)

    return RequestIntelligenceResponse(
        request_id=req.id,
        raw_text=req.raw_text,
        status=req.status,
        city=req.city,
        area=req.area,
        budget={
            "amount": req.budget_amount,
            "currency": req.budget_currency,
            "period": req.budget_period,
            "operator": req.budget_operator,
        } if req.budget_amount is not None else None,
        total_needs=total_needs,
        resolved_needs=resolved_count,
        progress_percentage=progress_pct,
        action_plan=action_plan,
        needs=needs_bundles,
        active_connections=active_conns,
        saved_resources=saved_resources_resp,
        resolution_summary=req.resolution_summary,
        resolved_at=req.resolved_at,
    )


# ============================================================================
# Need Progress & Resolution Tracking
# ============================================================================

def update_need_progress(
    db: Session,
    request_id: uuid.UUID,
    current_user: User,
    payload: NeedProgressUpdate,
) -> RequestIntelligenceResponse:
    """
    Updates progress on a specific extracted need category.
    Strictly validates resolved_entity_id against actual entities and ownership.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot update need progress.",
        )

    req = db.query(Request).filter(Request.id == request_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found.",
        )

    if req.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this request.",
        )

    norm_key = _normalize_need_key(payload.category)

    # Mandatory Adjustment 4: Server-Side Entity Validation
    if payload.resolved_entity_id:
        ent_id_str = payload.resolved_entity_id.strip()
        if payload.resolved_via == ResolutionSourceEnum.CONNECTION:
            try:
                conn_uuid = uuid.UUID(ent_id_str)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid connection UUID format.",
                )
            conn = db.query(Connection).filter(Connection.id == conn_uuid).first()
            if not conn:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Connection record not found.",
                )
            if conn.request_id != req.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Connection does not belong to this request.",
                )
            if conn.requester_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized for this connection.",
                )

        elif payload.resolved_via == ResolutionSourceEnum.COMMUNITY_QUESTION:
            try:
                q_uuid = uuid.UUID(ent_id_str)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid question UUID format.",
                )
            q = db.query(CommunityQuestion).filter(CommunityQuestion.id == q_uuid).first()
            if not q:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Community question not found.",
                )

        elif payload.resolved_via == ResolutionSourceEnum.SAVED_RESOURCE:
            saved = (
                db.query(RequestSavedResource)
                .filter(
                    RequestSavedResource.request_id == req.id,
                    (RequestSavedResource.place_id == ent_id_str),
                )
                .first()
            )
            if not saved:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Saved resource not found for this request.",
                )

        elif payload.resolved_via == ResolutionSourceEnum.SESSION:
            try:
                s_uuid = uuid.UUID(ent_id_str)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid session UUID format.",
                )
            sess = db.query(AssistanceSession).filter(AssistanceSession.id == s_uuid).first()
            if not sess:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Assistance session not found.",
                )
            if sess.request_id != req.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Assistance session is not linked to this request.",
                )
            if current_user.id not in [sess.proposer_id, sess.recipient_id]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not a participant in this assistance session.",
                )
            if sess.status != SessionStatus.COMPLETED.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only completed assistance sessions can resolve a need.",
                )

    # Update need_progress JSONB map
    progress_map = dict(req.need_progress or {})
    progress_map[norm_key] = {
        "category": payload.category,
        "status": payload.status.value,
        "resolved_via": payload.resolved_via.value if payload.resolved_via else None,
        "resolved_entity_id": payload.resolved_entity_id,
        "notes": payload.notes,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    req.need_progress = progress_map
    req.updated_at = datetime.now(timezone.utc)

    # Lifecycle state transition check
    extracted_needs = (req.extracted_requirements or {}).get("needs", [])
    total_count = len(extracted_needs) if extracted_needs else 1
    resolved_count = sum(
        1 for k, v in progress_map.items()
        if v.get("status") == NeedStatusEnum.RESOLVED.value
    )

    if resolved_count >= total_count:
        req.status = "RESOLVED"
        if not req.resolved_at:
            req.resolved_at = datetime.now(timezone.utc)
    elif resolved_count > 0:
        req.status = "PARTIALLY_RESOLVED"

    db.commit()
    db.refresh(req)

    return get_request_intelligence(db, req.id, current_user)


def resolve_overall_request(
    db: Session,
    request_id: uuid.UUID,
    current_user: User,
    payload: RequestResolvePayload,
) -> RequestIntelligenceResponse:
    """
    Explicit user resolution of overall request.
    Marks all untracked/open needs as resolved and sets terminal RESOLVED state.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot resolve requests.",
        )

    req = db.query(Request).filter(Request.id == request_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found.",
        )

    if req.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this request.",
        )

    now = datetime.now(timezone.utc)
    req.status = "RESOLVED"
    req.resolved_at = now
    if payload.resolution_summary:
        req.resolution_summary = payload.resolution_summary.strip()

    # Mark all needs as resolved in progress tracker
    progress_map = dict(req.need_progress or {})
    extracted_needs = (req.extracted_requirements or {}).get("needs", [])
    for n in extracted_needs:
        cat_key = _normalize_need_key(n.get("category", "general"))
        existing = progress_map.get(cat_key, {})
        existing["status"] = NeedStatusEnum.RESOLVED.value
        existing["resolved_via"] = existing.get("resolved_via") or ResolutionSourceEnum.MANUAL.value
        existing["updated_at"] = now.isoformat()
        progress_map[cat_key] = existing

    req.need_progress = progress_map
    req.updated_at = now

    db.commit()
    db.refresh(req)

    return get_request_intelligence(db, req.id, current_user)


# ============================================================================
# Saved Resources Management
# ============================================================================

def save_resource_for_request(
    db: Session,
    request_id: uuid.UUID,
    current_user: User,
    payload: SavedResourceCreate,
) -> SavedResourceResponse:
    """
    Save / bookmark a discovered place to a request.
    Maintains public place metadata only (NEVER private user coordinates).
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot save resources.",
        )

    req = db.query(Request).filter(Request.id == request_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found.",
        )

    if req.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to save resources to this request.",
        )

    # Upsert: if already saved for this request, update notes
    existing = (
        db.query(RequestSavedResource)
        .filter(
            RequestSavedResource.request_id == req.id,
            RequestSavedResource.place_id == payload.place_id,
        )
        .first()
    )
    if existing:
        if payload.notes is not None:
            existing.notes = payload.notes.strip()
        if payload.rating is not None:
            existing.rating = payload.rating
        if payload.user_ratings_total is not None:
            existing.user_ratings_total = payload.user_ratings_total
        db.commit()
        db.refresh(existing)
        return SavedResourceResponse.model_validate(existing)

    saved = RequestSavedResource(
        id=uuid.uuid4(),
        request_id=req.id,
        user_id=current_user.id,
        place_id=payload.place_id,
        name=payload.name.strip(),
        category=payload.category.strip(),
        formatted_address=payload.formatted_address.strip() if payload.formatted_address else None,
        rating=payload.rating,
        user_ratings_total=payload.user_ratings_total,
        latitude=payload.latitude,
        longitude=payload.longitude,
        notes=payload.notes.strip() if payload.notes else None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)

    return SavedResourceResponse.model_validate(saved)


def list_saved_resources_for_request(
    db: Session,
    request_id: uuid.UUID,
    current_user: User,
) -> List[SavedResourceResponse]:
    """List all saved / bookmarked resources for a request."""
    req = db.query(Request).filter(Request.id == request_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found.",
        )

    if req.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view saved resources for this request.",
        )

    records = (
        db.query(RequestSavedResource)
        .filter(RequestSavedResource.request_id == req.id)
        .order_by(RequestSavedResource.created_at.desc())
        .all()
    )
    return [SavedResourceResponse.model_validate(r) for r in records]


def delete_saved_resource_for_request(
    db: Session,
    request_id: uuid.UUID,
    place_id: str,
    current_user: User,
) -> None:
    """Delete a saved resource bookmark by place_id or saved record id."""
    req = db.query(Request).filter(Request.id == request_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found.",
        )

    if req.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete saved resources for this request.",
        )

    record = (
        db.query(RequestSavedResource)
        .filter(
            RequestSavedResource.request_id == req.id,
            RequestSavedResource.place_id == place_id,
        )
        .first()
    )
    if not record:
        try:
            rec_uuid = uuid.UUID(place_id)
            record = (
                db.query(RequestSavedResource)
                .filter(
                    RequestSavedResource.request_id == req.id,
                    RequestSavedResource.id == rec_uuid,
                )
                .first()
            )
        except (ValueError, TypeError):
            pass

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved resource not found.",
        )

    db.delete(record)
    db.commit()
