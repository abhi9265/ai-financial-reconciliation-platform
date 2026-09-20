"""FastAPI boundary around the reconciliation pipeline."""
from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from reconciliation_platform.ai.openai_reviewer import OpenAIReviewer
from reconciliation_platform.ai.reviewer import NoOpAIReviewer, escalate_reviews
from reconciliation_platform.config import Settings
from reconciliation_platform.decisioning.review import build_review_cases
from reconciliation_platform.evaluation.metrics import (
    evaluate_against_ground_truth,
    load_ground_truth,
)
from reconciliation_platform.observability import configure_logging, log_event
from reconciliation_platform.pipeline import run_pipeline, summarize
from reconciliation_platform.storage.sqlite import SQLiteStore

configure_logging()
app = FastAPI(title="AI Financial Reconciliation Platform", version="0.4.0")


class ReconciliationRequest(BaseModel):
    data_dir: str = Field(default="data/synthetic/seed")


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = Settings.from_env()
    if not settings.api_key_required:
        return
    if not settings.api_key or not x_api_key or not secrets.compare_digest(
        x_api_key, settings.api_key
    ):
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
        if not settings.api_key:
            raise HTTPException(status_code=503, detail="AI provider configured without API key")
        return OpenAIReviewer(
            api_key=settings.api_key,
            model=settings.ai_model,
            timeout=settings.ai_timeout_seconds,
        )
    return NoOpAIReviewer()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/reconcile")
def reconcile(
    request: ReconciliationRequest,
    _: None = Depends(require_api_key),
) -> dict:
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

    store = SQLiteStore(settings.database_path)
    inserted_reviews = store.save_review_cases(build_review_cases(result["decisions"]))
    summary["review_cases_persisted"] = inserted_reviews
    log_event("reconciliation_completed", **summary)
    return summary


@app.get("/storage/health")
def storage_health(_: None = Depends(require_api_key)) -> dict[str, int | str]:
    settings = Settings.from_env()
    store = SQLiteStore(settings.database_path)
    return {"status": "ok", "review_cases": store.review_case_count()}
