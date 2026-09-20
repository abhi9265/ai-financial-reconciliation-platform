"""FastAPI boundary around the reconciliation pipeline."""
from __future__ import annotations

import secrets
import tempfile
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from reconciliation_platform.ai.openai_reviewer import OpenAIReviewer
from reconciliation_platform.ai.reviewer import NoOpAIReviewer, escalate_reviews
from reconciliation_platform.config import Settings
from reconciliation_platform.decisioning.review import build_review_cases
from reconciliation_platform.evaluation.metrics import evaluate_against_ground_truth, load_ground_truth
from reconciliation_platform.observability import configure_logging, log_event
from reconciliation_platform.pipeline import run_pipeline, summarize
from reconciliation_platform.storage.factory import build_store
from reconciliation_platform.storage.object_store_factory import build_object_store
from reconciliation_platform.ingestion.uploads import build_object_key, validate_tenant_id
from reconciliation_platform.models.canonical_transaction import SourceSystem

configure_logging()
app = FastAPI(title="AI Financial Reconciliation Platform", version="0.5.0")


class ReconciliationRequest(BaseModel):
    data_dir: str = Field(default="data/synthetic/seed")


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = Settings.from_env()
    if not settings.api_key_required:
        return
    if not settings.api_key or not x_api_key or not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="invalid or missing API key")


def resolve_data_dir(data_dir: str) -> Path:
    requested = Path(data_dir).resolve()
    configured_root = Path("data").resolve()
    if not requested.is_dir() or (
        configured_root not in requested.parents and requested != configured_root
    ):
        raise HTTPException(status_code=403, detail="data directory is outside the allowed data root")
    return requested


def build_ai_reviewer(settings: Settings):
    if settings.ai_provider == "openai":
        if not settings.openai_api_key:
            raise HTTPException(status_code=503, detail="AI provider configured without OpenAI API key")
        return OpenAIReviewer(
            api_key=settings.openai_api_key,
            model=settings.ai_model,
            timeout=settings.ai_timeout_seconds,
        )
    return NoOpAIReviewer()


def require_tenant_id(x_tenant_id: str | None = Header(default=None)) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required")
    try:
        return validate_tenant_id(x_tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid tenant id") from exc


def _validate_upload(upload: UploadFile) -> None:
    if not upload.filename or not upload.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="only CSV uploads are supported")


@app.post("/v1/reconcile")
async def reconcile_uploaded_files(
    bank_file: UploadFile = File(...),
    purchase_file: UploadFile = File(...),
    _: None = Depends(require_api_key),
    tenant_id: str = Depends(require_tenant_id),
) -> dict:
    _validate_upload(bank_file)
    _validate_upload(purchase_file)
    settings = Settings.from_env()
    object_store = build_object_store(settings)
    bank_key = build_object_key(tenant_id, SourceSystem.BANK, bank_file.filename or "bank.csv")
    purchase_key = build_object_key(tenant_id, SourceSystem.PURCHASE_REGISTER, purchase_file.filename or "purchase.csv")
    bank_content = await bank_file.read()
    purchase_content = await purchase_file.read()
    max_bytes = 10 * 1024 * 1024
    if len(bank_content) > max_bytes or len(purchase_content) > max_bytes:
        raise HTTPException(status_code=413, detail="each upload must be <= 10 MiB")
    object_store.put(bank_key, bank_content)
    object_store.put(purchase_key, purchase_content)
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / "bank_transactions.csv").write_bytes(object_store.get(bank_key))
        (root / "purchase_invoices.csv").write_bytes(object_store.get(purchase_key))
        result = run_pipeline(root)
        summary = summarize(result)
        ai_results = escalate_reviews(result["decisions"], build_ai_reviewer(settings))
        summary["ai_review"] = {
            "provider": settings.ai_provider,
            "model": next(iter(ai_results.values())).model if ai_results else "none",
            "cases_reviewed": len(ai_results),
            "recommendations": {
                bank_id: {"recommendation": review.recommendation, "confidence": review.confidence, "rationale": review.rationale, "model": review.model}
                for bank_id, review in ai_results.items()
            },
        }
        store = build_store(settings)
        summary["review_cases_persisted"] = store.save_review_cases(
            build_review_cases(result["decisions"]), tenant_id=tenant_id
        )
    summary["tenant_id"] = tenant_id
    summary["objects"] = {"bank": bank_key, "purchase_register": purchase_key}
    log_event("tenant_reconciliation_completed", tenant_id=tenant_id, **summary)
    return summary


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def readiness() -> dict[str, str]:
    settings = Settings.from_env()
    try:
        store = build_store(settings)
        store.review_case_count()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="storage unavailable") from exc
    return {"status": "ready"}


@app.post("/reconcile")
def reconcile(request: ReconciliationRequest, _: None = Depends(require_api_key)) -> dict:
    settings = Settings.from_env()
    root = resolve_data_dir(request.data_dir)
    log_event("reconciliation_started", data_dir=str(root))
    result = run_pipeline(root)
    summary = summarize(result)

    truth_path = root / "ground_truth.csv"
    if truth_path.exists():
        metrics = evaluate_against_ground_truth(
            result["decisions"], load_ground_truth(truth_path)
        )
        summary["evaluation"] = {
            "precision": metrics.match_precision,
            "recall": metrics.match_recall,
            "f1": metrics.match_f1,
            "false_positive_rate": metrics.false_positive_rate,
            "exception_capture_rate": metrics.exception_capture_rate,
            "pair_accuracy": metrics.pair_accuracy,
        }

    ai_results = escalate_reviews(result["decisions"], build_ai_reviewer(settings))
    summary["ai_review"] = {
        "provider": settings.ai_provider,
        "model": next(iter(ai_results.values())).model if ai_results else "none",
        "cases_reviewed": len(ai_results),
        "recommendations": {
            bank_id: {
                "recommendation": review.recommendation,
                "confidence": review.confidence,
                "rationale": review.rationale,
                "model": review.model,
            }
            for bank_id, review in ai_results.items()
        },
    }

    store = build_store(settings)
    summary["review_cases_persisted"] = store.save_review_cases(
        build_review_cases(result["decisions"])
    )
    log_event("reconciliation_completed", **summary)
    return summary


@app.get("/storage/health")
def storage_health(_: None = Depends(require_api_key)) -> dict[str, int | str]:
    settings = Settings.from_env()
    store = build_store(settings)
    return {"status": "ok", "review_cases": store.review_case_count()}
