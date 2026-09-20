"""Tenant-scoped object storage abstraction."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ObjectStore(Protocol):
    def put(self, key: str, content: bytes) -> str: ...
    def get(self, key: str) -> bytes: ...


class LocalObjectStore:
    """Filesystem-backed object store for local development and tests."""

    def __init__(self, root: str | Path = "data/objects") -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if self.root not in candidate.parents:
            raise ValueError("object key escapes storage root")
        return candidate

    def put(self, key: str, content: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return key

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()


class S3ObjectStore:
    """S3-backed object store. Credentials are supplied by the AWS SDK environment."""

    def __init__(self, bucket: str, prefix: str = "") -> None:
        import boto3

        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.client = boto3.client("s3")

    def _key(self, key: str) -> str:
        return f"{self.prefix}/{key}".strip("/") if self.prefix else key

    def put(self, key: str, content: bytes) -> str:
        self.client.put_object(Bucket=self.bucket, Key=self._key(key), Body=content)
        return key

    def get(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=self._key(key))
        return response["Body"].read()
