"""End-to-end synthetic reconciliation pipeline."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from reconciliation_platform.anomaly.detector import detect_anomalies
from reconciliation_platform.ingestion.batch import (
    compute_batch_id,
    compute_file_fingerprint,
)
from reconciliation_platform.ingestion.contracts import validate_columns, validate_rows
from reconciliation_platform.models.canonical_transaction import SourceSystem
from reconciliation_platform.normalization.context import NormalizationContext
from reconciliation_platform.normalization.normalizer import normalize_rows
from reconciliation_platform.reconciliation.engine import reconcile
from reconciliation_platform.validation.rules import validate_transactions

SCHEMA_VERSION = "1.0"


def _read_csv(path: Path) -> tuple[list[dict[str, str]], str]:
    raw = path.read_bytes()
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"source file contains no data rows: {path.name}")
    return rows, compute_file_fingerprint(raw)


def run_pipeline(data_dir: str | Path) -> dict:
    root = Path(data_dir)
    bank_path = root / "bank_transactions.csv"
    purchase_path = root / "purchase_invoices.csv"

    bank_rows, bank_hash = _read_csv(bank_path)
    purchase_rows, purchase_hash = _read_csv(purchase_path)

    validate_columns(SourceSystem.BANK, bank_rows[0].keys())
    validate_rows(bank_rows, bank_rows[0].keys())
    validate_columns(SourceSystem.PURCHASE_REGISTER, purchase_rows[0].keys())
    validate_rows(purchase_rows, purchase_rows[0].keys())

    now = datetime.now(timezone.utc)
    bank_batch = compute_batch_id(SourceSystem.BANK, bank_hash, SCHEMA_VERSION)
    purchase_batch = compute_batch_id(
        SourceSystem.PURCHASE_REGISTER, purchase_hash, SCHEMA_VERSION
    )

    bank = normalize_rows(
        bank_rows,
        context=NormalizationContext(
            SourceSystem.BANK,
            bank_path.name,
            bank_hash,
            SCHEMA_VERSION,
            bank_batch,
            now,
        ),
    )
    purchase = normalize_rows(
        purchase_rows,
        context=NormalizationContext(
            SourceSystem.PURCHASE_REGISTER,
            purchase_path.name,
            purchase_hash,
            SCHEMA_VERSION,
            purchase_batch,
            now,
        ),
    )

    quality = validate_transactions(bank) + validate_transactions(purchase)
    decisions = reconcile(bank, purchase)
    anomalies = detect_anomalies(decisions, bank)

    return {
        "bank": bank,
        "purchase": purchase,
        "quality_issues": quality,
        "decisions": decisions,
        "anomalies": anomalies,
        "metadata": {
            "bank_file_hash": bank_hash,
            "purchase_file_hash": purchase_hash,
            "bank_batch_id": bank_batch,
            "purchase_batch_id": purchase_batch,
            "bank_rows": len(bank),
            "purchase_rows": len(purchase),
        },
    }


def summarize(result: dict) -> dict[str, int]:
    decisions = result["decisions"]
    return {
        "bank_rows": len(result["bank"]),
        "purchase_rows": len(result["purchase"]),
        "matched": sum(d.status == "MATCHED" for d in decisions),
        "review": sum(d.status == "REVIEW" for d in decisions),
        "unmatched": sum(d.status == "UNMATCHED" for d in decisions),
        "quality_issues": len(result["quality_issues"]),
        "anomalies": len(result["anomalies"]),
    }
