"""Batch identity and idempotency primitives."""
from __future__ import annotations
import hashlib
from reconciliation_platform.models.canonical_transaction import SourceSystem

def compute_file_fingerprint(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def compute_batch_id(source_system: SourceSystem, file_fingerprint: str, schema_version: str) -> str:
    payload = f"{source_system.value}|{file_fingerprint}|{schema_version}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]

def compute_idempotency_key(source_system: SourceSystem, source_record_id: str, record_hash: str) -> str:
    payload = f"{source_system.value}|{source_record_id}|{record_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
