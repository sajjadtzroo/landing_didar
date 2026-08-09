"""Media storage behind a tiny interface. LocalStorage for dev; MinioStorage
(S3-compatible) in prod so uploads survive container redeploys."""

import asyncio
import io
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Protocol

from app.core.config import settings


class Storage(Protocol):
    async def save(self, filename: str, data: bytes) -> str:
        """Persist bytes, return a loadable URL (or /media path in dev)."""
        ...


def _keyed_name(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower() or ".bin"
    return f"{uuid.uuid4().hex}{ext}"


class LocalStorage:
    def __init__(self) -> None:
        self.root = Path(settings.media_root)
        self.root.mkdir(parents=True, exist_ok=True)

    async def save(self, filename: str, data: bytes) -> str:
        name = _keyed_name(filename)
        # write off the event loop so a slow disk doesn't stall the worker
        await asyncio.to_thread((self.root / name).write_bytes, data)
        return f"{settings.media_url_prefix}/{name}"


class MinioStorage:
    """S3-compatible object storage (Liara / MinIO). Uploads under `uploads/` with
    a uuid name. The bucket stays PRIVATE — objects are served back through the
    app's own /media route (see main.py), which streams them with credentials, so
    the returned value is a stable `/media/<key>` path (not a public bucket URL)."""

    def __init__(self) -> None:
        from minio import Minio

        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._bucket = settings.minio_bucket

    async def save(self, filename: str, data: bytes) -> str:
        key = f"uploads/{_keyed_name(filename)}"
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        await asyncio.to_thread(
            self._client.put_object,
            self._bucket,
            key,
            io.BytesIO(data),
            len(data),
            content_type,
        )
        return f"{settings.media_url_prefix}/{key}"

    def open(self, key: str):
        """Return the object's streaming response (urllib3). Caller reads, then
        close()/release_conn(). Raises minio.error.S3Error if the key is absent."""
        return self._client.get_object(self._bucket, key)


_storage: Storage | None = None


def get_storage() -> Storage:
    # Memoized: MinIO when configured (prod), else local disk (dev).
    global _storage
    if _storage is None:
        configured = bool(
            settings.minio_endpoint
            and settings.minio_bucket
            and settings.minio_access_key
        )
        _storage = MinioStorage() if configured else LocalStorage()
    return _storage
