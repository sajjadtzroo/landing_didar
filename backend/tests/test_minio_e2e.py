"""End-to-end test of the MinIO photo import against a REAL MinIO server.

Skipped unless MINIO_TEST_ENDPOINT is set (mirrors how the suite needs a real
Postgres). Spin one up with:

    docker run -d -p 9100:9000 -e MINIO_ROOT_USER=minioadmin \
        -e MINIO_ROOT_PASSWORD=minioadmin quay.io/minio/minio server /data
    MINIO_TEST_ENDPOINT=localhost:9100 pytest tests/test_minio_e2e.py

It uploads real objects under `{sku}/`, runs the real import (which builds a real
Minio client from settings, lists + downloads), then asserts the files landed on
local media, the product rows were updated, and the PUBLIC API exposes the gallery.
"""

import io
import os

import pytest
from sqlalchemy import select

import app.domains.catalog.minio_import as mod
from app.core.config import settings
from app.domains.catalog import Product

_ENDPOINT = os.getenv("MINIO_TEST_ENDPOINT")
_KEY = os.getenv("MINIO_TEST_ACCESS_KEY", "minioadmin")
_SECRET = os.getenv("MINIO_TEST_SECRET_KEY", "minioadmin")

pytestmark = [
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.skipif(
        not _ENDPOINT, reason="set MINIO_TEST_ENDPOINT to run the MinIO e2e test"
    ),
]


@pytest.fixture
def minio_bucket():
    """A real bucket seeded with one product folder (2 images + 1 non-image)."""
    from minio import Minio

    client = Minio(_ENDPOINT, access_key=_KEY, secret_key=_SECRET, secure=False)
    bucket = "didar-e2e"
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    objects = {
        "e2e-sku/2.png": b"two",        # uploaded out of order -> tests sorting
        "e2e-sku/1.jpg": b"one",
        "e2e-sku/readme.txt": b"ignore",  # non-image -> filtered out
    }
    for key, data in objects.items():
        client.put_object(bucket, key, io.BytesIO(data), length=len(data))
    yield client, bucket
    for obj in client.list_objects(bucket, recursive=True):
        client.remove_object(bucket, obj.object_name)
    client.remove_bucket(bucket)


async def test_import_end_to_end_from_real_minio(
    _sessionmaker, client, monkeypatch, tmp_path, minio_bucket
):
    _, bucket = minio_bucket
    monkeypatch.setattr(settings, "media_root", str(tmp_path))
    monkeypatch.setattr(settings, "media_url_prefix", "/media")
    monkeypatch.setattr(settings, "minio_endpoint", _ENDPOINT)
    monkeypatch.setattr(settings, "minio_access_key", _KEY)
    monkeypatch.setattr(settings, "minio_secret_key", _SECRET)
    monkeypatch.setattr(settings, "minio_bucket", bucket)
    monkeypatch.setattr(settings, "minio_secure", False)
    monkeypatch.setattr(mod, "SessionLocal", _sessionmaker)

    async with _sessionmaker() as db:
        db.add(Product(name="E2E Ring", slug="e2e-ring", sku="e2e-sku"))
        db.add(Product(name="No Photos", slug="no-photos", sku="no-folder-sku"))
        await db.commit()

    # Real import — no client injected, so _make_client() builds a real MinIO client.
    summary = await mod.import_product_images()
    assert summary["photos"] == 2
    assert "no-folder-sku" in summary["skipped"]

    # Bytes were really pulled from MinIO onto the local media store.
    assert (tmp_path / "products/e2e-sku/1.jpg").read_bytes() == b"one"
    assert (tmp_path / "products/e2e-sku/2.png").read_bytes() == b"two"
    assert not (tmp_path / "products/e2e-sku/readme.txt").exists()

    # DB rows updated (sorted, image-only; first = primary).
    async with _sessionmaker() as db:
        p = (
            await db.execute(select(Product).where(Product.sku == "e2e-sku"))
        ).scalar_one()
        assert p.images == [
            "/media/products/e2e-sku/1.jpg",
            "/media/products/e2e-sku/2.png",
        ]
        assert p.image_url == "/media/products/e2e-sku/1.jpg"

    # The public API now serves the gallery (what the frontend product page reads).
    r = await client.get("/api/v1/products/e2e-ring")
    assert r.status_code == 200, r.text
    assert r.json()["images"] == [
        "/media/products/e2e-sku/1.jpg",
        "/media/products/e2e-sku/2.png",
    ]


async def test_import_is_idempotent_on_rerun(
    _sessionmaker, monkeypatch, tmp_path, minio_bucket
):
    _, bucket = minio_bucket
    monkeypatch.setattr(settings, "media_root", str(tmp_path))
    monkeypatch.setattr(settings, "media_url_prefix", "/media")
    monkeypatch.setattr(settings, "minio_endpoint", _ENDPOINT)
    monkeypatch.setattr(settings, "minio_access_key", _KEY)
    monkeypatch.setattr(settings, "minio_secret_key", _SECRET)
    monkeypatch.setattr(settings, "minio_bucket", bucket)
    monkeypatch.setattr(settings, "minio_secure", False)
    monkeypatch.setattr(mod, "SessionLocal", _sessionmaker)

    async with _sessionmaker() as db:
        db.add(Product(name="E2E Ring", slug="e2e-ring", sku="e2e-sku"))
        await db.commit()

    first = await mod.import_product_images()
    second = await mod.import_product_images()  # re-run must not duplicate
    assert first["photos"] == second["photos"] == 2

    async with _sessionmaker() as db:
        p = (
            await db.execute(select(Product).where(Product.sku == "e2e-sku"))
        ).scalar_one()
        assert len(p.images) == 2  # stable, not appended
