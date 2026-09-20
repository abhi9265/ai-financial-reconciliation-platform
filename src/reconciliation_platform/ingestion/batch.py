"""Batch identity and record-level idempotency primitives."""
from __future__ import annotations

import hashlib

from reconciliation_platform.models.canonical_transaction import CanonicalTransaction, SourceSystem


def compute_file_fingerprint(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def compute_batch_id(source_system: SourceSystem, file_fingerprint: str, schema_version: str) -> str:
    payload = f"{source_system.value}|{file_fingerprint}|{schema_version}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def compute_idempotency_key(source_system: SourceSystem, source_record_id: str, record_hash: str) -> str:
    payload = f"{source_system.value}|{source_record_id}|{record_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_idempotency_keys(
    transactions: list[CanonicalTransaction],
) -> dict[str, str]:
    return {
        tx.source_record_id: compute_idempotency_key(
            tx.source_system, tx.source_record_id, tx.record_hash
        )
        for tx in transactions
    }


def find_duplicate_idempotency_keys(keys: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for key in keys:
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return duplicates
