"""S3-compatible object storage abstraction scaffold."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class StoredObject:
    key: str
    content_type: str
    size_bytes: int


class ObjectStorageService:
    """Abstraction layer for object storage providers (S3/MinIO/GCS)."""

    def put(self, key: str, content: bytes, content_type: str) -> StoredObject:
        # TODO: Implement concrete provider adapter.
        return StoredObject(key=key, content_type=content_type, size_bytes=len(content))

    def get(self, key: str) -> bytes:
        # TODO: Implement concrete provider adapter.
        raise NotImplementedError
