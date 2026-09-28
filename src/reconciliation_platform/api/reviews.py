"""Tenant-scoped human review workflow endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from reconciliation_platform.audit import record_audit_event
from reconciliation_platform.config import Settings
from reconciliation_platform.storage.factory import build_store
from reconciliation_platform.ingestion.uploads import validate_tenant_id
from reconciliation_platform.api.app_auth import require_api_key, require_tenant_id

router = APIRouter(prefix="/v1/reviews", tags=["reviews"])


class BulkReviewDecisionRequest(BaseModel):
    case_ids: list[str] = Field(min_length=1, max_length=50)
    action: str = Field(pattern="^(approve|reject)$")
    note: str | None = Field(default=None, max_length=2000)


class ReviewDecisionRequest(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    note: str | None = Field(default=None, max_length=2000)


def _tenant(tenant_id: str) -> str:
    try:
        return validate_tenant_id(tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid tenant id") from exc


@router.get("", summary="List the tenant review queue")
def list_reviews(
    status: str = "open",
    limit: int = 50,
    offset: int = 0,
    _: None = Depends(require_api_key),
    tenant_id: str = Depends(require_tenant_id),
) -> dict:
    if status not in {"open", "approved", "rejected", "all"}:
        raise HTTPException(status_code=400, detail="status must be open, approved, rejected, or all")
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be >= 0")
    store = build_store(Settings.from_env())
    items, total = store.list_review_cases(tenant_id=tenant_id, status=status, limit=limit, offset=offset)
    return {
        "tenant_id": tenant_id,
        "status": status,
        "limit": limit,
        "offset": offset,
        "total": total,
        "items": items,
    }


@router.post("/{case_id}/decision", summary="Approve or reject a review case")
def decide_review(
    case_id: str,
    request: ReviewDecisionRequest,
    _: None = Depends(require_api_key),
    tenant_id: str = Depends(require_tenant_id),
) -> dict:
    store = build_store(Settings.from_env())
    case = store.get_review_case(case_id, tenant_id=tenant_id)
    if case is None:
        raise HTTPException(status_code=404, detail="review case not found")
    if case["status"] != "open":
        raise HTTPException(status_code=409, detail="review case is already resolved")
    updated = store.resolve_review_case(
        case_id,
        tenant_id=tenant_id,
        status="approved" if request.action == "approve" else "rejected",
        note=request.note,
    )
    if not updated:
        raise HTTPException(status_code=409, detail="review case could not be resolved")
    record_audit_event(
        "review_case.decided",
        tenant_id=tenant_id,
        case_id=case_id,
        action=request.action,
        note=request.note,
    )
    return store.get_review_case(case_id, tenant_id=tenant_id)


@router.post("/bulk-decision", summary="Approve or reject multiple review cases")
def bulk_decide_reviews(
    request: BulkReviewDecisionRequest,
    _: None = Depends(require_api_key),
    tenant_id: str = Depends(require_tenant_id),
) -> dict:
    store = build_store(Settings.from_env())
    resolved = []
    conflicts = []
    for case_id in request.case_ids:
        case = store.get_review_case(case_id, tenant_id=tenant_id)
        if case is None:
            conflicts.append({"case_id": case_id, "reason": "not_found"})
            continue
        if case["status"] != "open":
            conflicts.append({"case_id": case_id, "reason": "already_resolved"})
            continue
        updated = store.resolve_review_case(
            case_id, tenant_id=tenant_id,
            status="approved" if request.action == "approve" else "rejected",
            note=request.note,
        )
        if updated:
            resolved.append(case_id)
            record_audit_event("review_case.decided", tenant_id=tenant_id, case_id=case_id, action=request.action, note=request.note)
        else:
            conflicts.append({"case_id": case_id, "reason": "concurrent_update"})
    return {"tenant_id": tenant_id, "action": request.action, "resolved": resolved, "conflicts": conflicts}


@router.get("/{case_id}", summary="Get a review case")
def get_review(
    case_id: str,
    _: None = Depends(require_api_key),
    tenant_id: str = Depends(require_tenant_id),
) -> dict:
    case = build_store(Settings.from_env()).get_review_case(case_id, tenant_id=tenant_id)
    if case is None:
        raise HTTPException(status_code=404, detail="review case not found")
    return case
