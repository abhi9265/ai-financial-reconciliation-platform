from pathlib import Path

from reconciliation_platform.storage.object_store import LocalObjectStore


def test_local_object_store_round_trip(tmp_path: Path):
    store = LocalObjectStore(tmp_path)
    key = "tenants/acme/raw/bank/file.csv"
    assert store.put(key, b"a,b\n1,2\n") == key
    assert store.get(key) == b"a,b\n1,2\n"


def test_local_object_store_rejects_path_escape(tmp_path: Path):
    store = LocalObjectStore(tmp_path)
    try:
        store.get("../outside")
    except ValueError:
        pass
    else:
        raise AssertionError("path traversal must be rejected")
