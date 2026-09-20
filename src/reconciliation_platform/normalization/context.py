"""Normalization context shared by source adapters."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from reconciliation_platform.models.canonical_transaction import SourceSystem

@dataclass(frozen=True)
class NormalizationContext:
    source_system: SourceSystem
    source_file_name: str
    source_file_hash: str
    source_schema_version: str
    ingestion_batch_id: str
    ingested_at: datetime
    currency: str = "INR"
