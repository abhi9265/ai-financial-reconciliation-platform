import pytest
from fastapi import HTTPException, UploadFile
from io import BytesIO

from reconciliation_platform.api.app import (
    _read_upload_limited,
    _validate_upload,
    build_ai_reviewer,
    resolve_data_dir,
)
from reconciliation_platform.config import Settings
from reconciliation_platform.models.canonical_transaction import SourceSystem


def _upload(name: str) -> UploadFile:
    return UploadFile(file=BytesIO(b"payload"), filename=name)


def test_resolve_data_dir_rejects_missing_or_outside_root(tmp_path):
    with pytest.raises(HTTPException) as missing:
        resolve_data_dir(str(tmp_path / "missing"))
    assert missing.value.status_code == 403


def test_validate_upload_enforces_source_extensions():
    with pytest.raises(HTTPException):
        _validate_upload(_upload("gst.csv"), SourceSystem.GST)
    with pytest.raises(HTTPException):
        _validate_upload(_upload("tally.json"), SourceSystem.TALLY)
    with pytest.raises(HTTPException):
        _validate_upload(_upload("bank.xlsx"), SourceSystem.BANK)
    with pytest.raises(HTTPException):
        _validate_upload(_upload("purchase.json"), SourceSystem.PURCHASE_REGISTER)


def test_validate_upload_rejects_missing_filename():
    upload = UploadFile(file=BytesIO(b"payload"), filename=None)
    with pytest.raises(HTTPException) as exc:
        _validate_upload(upload, SourceSystem.BANK)
    assert exc.value.status_code == 415


def test_build_ai_reviewer_requires_key_for_openai(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        build_ai_reviewer(Settings.from_env())
    assert exc.value.status_code == 503


def test_build_ai_reviewer_uses_noop_by_default(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "none")
    reviewer = build_ai_reviewer(Settings.from_env())
    assert reviewer.__class__.__name__ == "NoOpAIReviewer"


@pytest.mark.asyncio
async def test_read_upload_limited_rejects_oversized_payload():
    upload = UploadFile(file=BytesIO(b"x" * (10 * 1024 * 1024 + 1)), filename="large.csv")
    with pytest.raises(HTTPException) as exc:
        await _read_upload_limited(upload)
    assert exc.value.status_code == 413
