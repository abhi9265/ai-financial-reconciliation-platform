"""Small, explicit Bronze/Silver/Gold data-lake layer.

Raw source rows are preserved in Bronze, validated canonical rows are written to
Silver, and reconciliation decisions are written to Gold. Invalid rows are
quarantined with reason codes so reprocessing remains possible.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import pandas as pd

from reconciliation_platform.models.canonical_transaction import CanonicalTransaction


@dataclass(frozen=True)
class DataQualityIssue:
    row_number: int
    code: str
    message: str


def _write_parquet(rows: Sequence[Mapping[str, object]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(list(rows)).to_parquet(path, index=False)
    return path


def write_bronze(rows: Iterable[Mapping[str, object]], root: str | Path, batch_id: str) -> Path:
    """Persist source rows unchanged for replay and lineage."""
    return _write_parquet(list(rows), Path(root) / "bronze" / f"batch_id={batch_id}" / "records.parquet")


def write_silver(
    transactions: Iterable[CanonicalTransaction],
    root: str | Path,
    batch_id: str,
) -> tuple[Path, Path]:
    """Validate canonical records and write valid rows plus quarantine."""
    valid: list[dict[str, object]] = []
    quarantine: list[dict[str, object]] = []
    for row_number, tx in enumerate(transactions, start=1):
        try:
            validated = CanonicalTransaction.model_validate(tx.model_dump())
            valid.append(validated.model_dump(mode="json"))
        except Exception as exc:
            quarantine.append(asdict(DataQualityIssue(row_number, "CANONICAL_VALIDATION", str(exc))))
    silver_path = _write_parquet(valid, Path(root) / "silver" / f"batch_id={batch_id}" / "transactions.parquet")
    quarantine_path = _write_parquet(quarantine, Path(root) / "quarantine" / f"batch_id={batch_id}" / "rejected.parquet")
    return silver_path, quarantine_path


def write_gold(decisions: Iterable[Mapping[str, object]], root: str | Path, batch_id: str) -> Path:
    """Persist auditable reconciliation outcomes as queryable Gold data."""
    return _write_parquet(
        list(decisions),
        Path(root) / "gold" / f"batch_id={batch_id}" / "reconciliation_decisions.parquet",
    )
