"""Validation and tenant-scoped naming for uploaded source files."""
from __future__ import annotations

import re
from pathlib import PurePosixPath

from reconciliation_platform.models.canonical_transaction import SourceSystem

_TENANT_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


def validate_tenant_id(tenant_id: str) -> str:
    value = tenant_id.strip()
    if not _TENANT_PATTERN.fullmatch(value):
        raise ValueError("invalid tenant id")
    return value


def build_object_key(tenant_id: str, source_system: SourceSystem, filename: str) -> str:
    tenant = validate_tenant_id(tenant_id)
    safe_name = PurePosixPath(filename or "upload.csv").name
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", safe_name)
    if not safe_name.lower().endswith(".csv"):
        raise ValueError("only CSV uploads are supported")
    return f"tenants/{tenant}/raw/{source_system.value.lower()}/{safe_name}"
