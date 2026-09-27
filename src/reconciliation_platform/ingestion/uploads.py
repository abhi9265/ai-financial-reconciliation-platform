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
    suffix = safe_name.lower().rsplit(".", 1)[-1] if "." in safe_name else ""
    if suffix not in {"csv", "json", "xlsx"}:
        raise ValueError("only CSV, JSON, and XLSX uploads are supported")
    if source_system is SourceSystem.GST and suffix != "json":
        raise ValueError("GST uploads must be JSON")
    if source_system is SourceSystem.TALLY and suffix not in {"csv", "xlsx"}:
        raise ValueError("Tally uploads must be CSV or XLSX")
    if source_system is not SourceSystem.GST and source_system is not SourceSystem.TALLY and suffix != "csv":
        raise ValueError(f"{source_system.value} uploads must be CSV")
    return f"tenants/{tenant}/raw/{source_system.value.lower()}/{safe_name}"
