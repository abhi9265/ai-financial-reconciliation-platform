"""FastAPI boundary around the reconciliation pipeline."""
from __future__ import annotations

import os\nfrom pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from reconciliation_platform.evaluation.metrics import evaluate_against_ground_truth, load_ground_truth
from reconciliation_platform.observability import configure_logging, log_event
from reconciliation_platform.pipeline import run_pipeline, summarize\nfrom reconciliation_platform.decisioning.review import build_review_cases\nfrom reconciliation_platform.storage.sqlite import SQLiteStore
from reconciliation_platform.storage.sqlite import SQLiteStore

configure_logging()
app = FastAPI(title="AI Financial Reconciliation Platform", version="0.3.0")\n

class ReconciliationRequest(BaseModel):
    data_dir: str = Field(default="data/synthetic/seed")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/reconcile")
def reconcile(request: ReconciliationRequest) -> dict:
    root = Path(request.data_dir)
    if not root.exists():
        raise HTTPException(status_code=404, detail="data directory not found")

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

    log_event("reconciliation_completed", **summary)
    return summary


@app.get("/storage/health")
def storage_health() -> dict[str, int | str]:
    store = SQLiteStore(os.getenv("RECONCILIATION_DB", "data/reconciliation.db"))
    return {"status": "ok", "review_cases": store.review_case_count()}
