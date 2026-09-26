"""FastAPI boundary around the reconciliation pipeline."""
from __future__ import annotations

import secrets
import tempfile
import uuid
import time

from fastapi.responses import Response
from fastapi import BackgroundTasks
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from reconciliation_platform.ai.openai_reviewer import OpenAIReviewer
from reconciliation_platform.ai.reviewer import NoOpAIReviewer, escalate_reviews
from reconciliation_platform.config import Settings
from reconciliation_platform.decisioning.review import build_review_cases
from reconciliation_platform.evaluation.metrics import evaluate_against_ground_truth, load_ground_truth
from reconciliation_platform.observability import configure_logging, log_event, set_request_id
from reconciliation_platform.audit import read_audit_events, record_audit_event
from reconciliation_platform.metrics import observe_http, prometheus_payload, record_reconciliation, snapshot, set_review_backlog
from reconciliation_platform.pipeline import run_pipeline, summarize
from reconciliation_platform.storage.factory import build_store
from reconciliation_platform.storage.object_store_factory import build_object_store
from reconciliation_platform.ingestion.uploads import build_object_key, validate_tenant_id
from reconciliation_platform.models.canonical_transaction import SourceSystem
from reconciliation_platform.rate_limit import build_rate_limiter

configure_logging()
app = FastAPI(title="AI Financial Reconciliation Platform", version="0.5.0")


@app.middleware("http")
async def request_context(request, call_next):
    request_id = set_request_id(request.headers.get("X-Request-ID"))
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration = time.perf_counter() - started
        observe_http(request.method, request.url.path, 500, duration)
        log_event("http_request", request_id=request_id, method=request.method, path=request.url.path, status_code=500, duration_ms=round(duration * 1000, 2))
        raise
    duration = time.perf_counter() - started
    observe_http(request.method, request.url.path, response.status_code, duration)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    log_event("http_request", request_id=request_id, method=request.method, path=request.url.path, status_code=response.status_code, duration_ms=round(duration * 1000, 2))
    return response


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


def require_tenant_id(
    x_api_key: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
) -> str:
    settings = Settings.from_env()
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required")
    if settings.tenant_api_keys:
        if not x_api_key:
            raise HTTPException(status_code=401, detail="tenant API key is required")
        tenant = settings.tenant_api_keys.get(x_api_key)
        if tenant is None:
            raise HTTPException(status_code=401, detail="invalid tenant credentials")
        if tenant != x_tenant_id:
            raise HTTPException(status_code=403, detail="API key is not authorized for this tenant")
    try:
        return validate_tenant_id(x_tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid tenant id") from exc


def _validate_upload(upload: UploadFile) -> None:
    if not upload.filename or not upload.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="only CSV uploads are supported")


async def _read_upload_limited(upload: UploadFile, max_bytes: int = 10 * 1024 * 1024) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(status_code=413, detail="each upload must be <= 10 MiB")
        chunks.append(chunk)
    return b"".join(chunks)


@app.post("/v1/reconcile")
async def reconcile_uploaded_files(
    bank_file: UploadFile = File(...),  # noqa: B008
    purchase_file: UploadFile = File(...),  # noqa: B008
    _: None = Depends(require_api_key),
    tenant_id: str = Depends(require_tenant_id),
) -> dict:
    _validate_upload(bank_file)
    _validate_upload(purchase_file)
    settings = Settings.from_env()
    if not build_rate_limiter(settings).allow(tenant_id):
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    object_store = build_object_store(settings)
    bank_key = build_object_key(tenant_id, SourceSystem.BANK, bank_file.filename or "bank.csv")
    purchase_key = build_object_key(tenant_id, SourceSystem.PURCHASE_REGISTER, purchase_file.filename or "purchase.csv")
    bank_content = await _read_upload_limited(bank_file)
    purchase_content = await _read_upload_limited(purchase_file)
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
    record_reconciliation(summary, mode="sync")
    set_review_backlog(store.review_case_count(tenant_id=tenant_id))
    record_audit_event("reconciliation.completed", tenant_id=tenant_id, mode="sync", summary=summary)
    log_event("tenant_reconciliation_completed", **summary)
    return summary


def _run_reconciliation_job(job_id: str, tenant_id: str, bank_key: str, purchase_key: str, *, raise_on_error: bool = False) -> None:
    settings = Settings.from_env()
    store = build_store(settings)
    store.update_job(job_id, tenant_id=tenant_id, status="running")
    try:
        object_store = build_object_store(settings)
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
                    bank_id: {
                        "recommendation": review.recommendation,
                        "confidence": review.confidence,
                        "rationale": review.rationale,
                        "model": review.model,
                    }
                    for bank_id, review in ai_results.items()
                },
            }
            summary["review_cases_persisted"] = store.save_review_cases(
                build_review_cases(result["decisions"]), tenant_id=tenant_id
            )
            summary["tenant_id"] = tenant_id
            summary["objects"] = {"bank": bank_key, "purchase_register": purchase_key}
        record_reconciliation(summary, mode="async")
        set_review_backlog(store.review_case_count(tenant_id=tenant_id))
        record_audit_event(
            "reconciliation.job.completed",
            tenant_id=tenant_id,
            job_id=job_id,
            mode="async",
            status="succeeded",
            summary=summary,
        )
        store.update_job(job_id, tenant_id=tenant_id, status="succeeded", result=summary)
        log_event("reconciliation_job_completed", job_id=job_id, tenant_id=tenant_id)
    except Exception as exc:
        record_reconciliation({}, failed=True, mode="async")
        record_audit_event(
            "reconciliation.job.failed",
            tenant_id=tenant_id,
            job_id=job_id,
            mode="async",
            status="failed",
            error=str(exc),
        )
        store.update_job(job_id, tenant_id=tenant_id, status="failed", error=str(exc))
        log_event("reconciliation_job_failed", job_id=job_id, tenant_id=tenant_id, error=str(exc))
        if raise_on_error:
            raise


@app.post("/v1/reconcile/async", status_code=202)
async def enqueue_reconciliation(
    background_tasks: BackgroundTasks,
    bank_file: UploadFile = File(...),  # noqa: B008
    purchase_file: UploadFile = File(...),  # noqa: B008
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    _: None = Depends(require_api_key),
    tenant_id: str = Depends(require_tenant_id),
) -> dict:
    _validate_upload(bank_file)
    _validate_upload(purchase_file)
    if idempotency_key is not None and not 1 <= len(idempotency_key) <= 255:
        raise HTTPException(status_code=400, detail="Idempotency-Key must be 1-255 characters")
    settings = Settings.from_env()
    if not build_rate_limiter(settings).allow(tenant_id):
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    object_store = build_object_store(settings)
    bank_key = build_object_key(tenant_id, SourceSystem.BANK, bank_file.filename or "bank.csv")
    purchase_key = build_object_key(tenant_id, SourceSystem.PURCHASE_REGISTER, purchase_file.filename or "purchase.csv")
    bank_content = await _read_upload_limited(bank_file)
    purchase_content = await _read_upload_limited(purchase_file)
    object_store.put(bank_key, bank_content)
    object_store.put(purchase_key, purchase_content)
    job_id = uuid.uuid4().hex
    store = build_store(settings)
    existing_or_created_job_id = store.create_job(
        job_id=job_id,
        tenant_id=tenant_id,
        bank_key=bank_key,
        purchase_key=purchase_key,
        idempotency_key=idempotency_key,
    )
    if existing_or_created_job_id != job_id:
        existing_job = store.get_job(existing_or_created_job_id, tenant_id=tenant_id)
        return {
            "job_id": existing_or_created_job_id,
            "tenant_id": tenant_id,
            "status": existing_job["status"] if existing_job else "queued",
            "idempotent_replay": True,
        }
    if settings.job_queue == "celery":
        from reconciliation_platform.worker import process_job
        process_job.delay(job_id, tenant_id, bank_key, purchase_key)
    else:
        background_tasks.add_task(_run_reconciliation_job, job_id, tenant_id, bank_key, purchase_key)
    return {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "queued",
        "objects": {"bank": bank_key, "purchase_register": purchase_key},
    }


@app.get("/v1/reconcile/jobs/{job_id}")
def reconciliation_job_status(
    job_id: str,
    _: None = Depends(require_api_key),
    tenant_id: str = Depends(require_tenant_id),
) -> dict:
    job = build_store(Settings.from_env()).get_job(job_id, tenant_id=tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    record_audit_event("reconciliation.job.status_read", tenant_id=tenant_id, job_id=job_id, status=job["status"])
    return job


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def readiness() -> dict[str, str]:
    settings = Settings.from_env()
    try:
        store = build_store(settings)
        store.review_case_count()
        if settings.job_queue == "celery":
            import redis
            redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2).ping()
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
    record_reconciliation(summary)
    record_audit_event("reconciliation.completed", tenant_id="default", mode="sync", summary=summary)
    log_event("reconciliation_completed", **summary)
    return summary


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(content=prometheus_payload(), media_type="text/plain; version=0.0.4")


@app.get("/metrics/snapshot", include_in_schema=False)
def metrics_snapshot() -> dict[str, int]:
    return snapshot()


@app.get("/v1/audit")
def audit_events(
    limit: int = 100,
    _: None = Depends(require_api_key),
    tenant_id: str = Depends(require_tenant_id),
) -> dict:
    if limit > 500:
        raise HTTPException(status_code=400, detail="limit must be <= 500")
    return {"tenant_id": tenant_id, "events": read_audit_events(tenant_id=tenant_id, limit=limit)}


@app.get("/storage/health")
def storage_health(_: None = Depends(require_api_key)) -> dict[str, int | str]:
    settings = Settings.from_env()
    store = build_store(settings)
    return {"status": "ok", "review_cases": store.review_case_count()}
