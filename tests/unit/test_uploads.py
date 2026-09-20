import pytest

from reconciliation_platform.ingestion.uploads import build_object_key, validate_tenant_id
from reconciliation_platform.models.canonical_transaction import SourceSystem


def test_validate_tenant_id():
    assert validate_tenant_id("acme_01") == "acme_01"
    with pytest.raises(ValueError):
        validate_tenant_id("../acme")


def test_build_object_key_is_tenant_scoped():
    key = build_object_key("acme_01", SourceSystem.BANK, "../../bank.csv")
    assert key == "tenants/acme_01/raw/bank/bank.csv"


def test_build_object_key_rejects_non_csv():
    with pytest.raises(ValueError):
        build_object_key("acme_01", SourceSystem.BANK, "bank.xlsx")
