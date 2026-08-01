"""Local media storage with a small interface so it can be swapped for
S3-compatible object storage in production without touching callers."""

import asyncio
import os
import uuid
from pathlib import Path
from typing import Protocol

from app.core.config import settings


class Storage(Protocol):
    async def save(self, filename: str, data: bytes) -> str:
        """Persist bytes, return a public URL path."""
        ...


class LocalStorage:
    def __init__(self) -> None:
        self.root = Path(settings.media_root)
        self.root.mkdir(parents=True, exist_ok=True)

    async def save(self, filename: str, data: bytes) -> str:
        ext = os.path.splitext(filename)[1].lower() or ".bin"
        name = f"{uuid.uuid4().hex}{ext}"
        # write off the event loop so a slow disk doesn't stall the worker
        await asyncio.to_thread((self.root / name).write_bytes, data)
        return f"{settings.media_url_prefix}/{name}"


def get_storage() -> Storage:
    # ponytail: one impl now; add S3Storage(Protocol) and branch here at deploy.
    return LocalStorage()
