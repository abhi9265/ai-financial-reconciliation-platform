"""Build the configured object storage backend."""
from __future__ import annotations

from reconciliation_platform.config import Settings
from reconciliation_platform.storage.object_store import LocalObjectStore, S3ObjectStore


def build_object_store(settings: Settings):
    if settings.object_store == "s3":
        if not settings.s3_bucket:
            raise ValueError("OBJECT_STORE=s3 requires S3_BUCKET")
        return S3ObjectStore(settings.s3_bucket, settings.s3_prefix)
    return LocalObjectStore(settings.object_store_path)
