"""Shared authentication dependencies for API routers."""
from __future__ import annotations

import secrets

from fastapi import Header, HTTPException

from reconciliation_platform.config import Settings
from reconciliation_platform.ingestion.uploads import validate_tenant_id


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    settings = Settings.from_env()
    if not settings.api_key_required:
        return
    if not settings.api_key or not x_api_key or not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="invalid or missing API key")


def require_tenant_id(
    x_api_key: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
) -> str:
    settings = Settings.from_env()
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required")
    if settings.tenant_api_keys:
        if not x_api_key:
            raise HTTPException(status_code=401, detail="tenant API key is required")
        tenant = settings.tenant_api_keys.get(x_api_key)
        if tenant is None:
            raise HTTPException(status_code=401, detail="invalid tenant credentials")
        if tenant != x_tenant_id:
            raise HTTPException(status_code=403, detail="API key is not authorized for this tenant")
    try:
        return validate_tenant_id(x_tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid tenant id") from exc
