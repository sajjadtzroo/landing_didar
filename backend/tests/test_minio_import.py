"""Unit test for the MinIO photo import. The MinIO client is faked (in-memory
tree) — no network, no minio server. DB is the test session; media_root is tmp."""


import pytest
from sqlalchemy import select

import app.domains.catalog.minio_import as mod
from app.core.config import settings
from app.domains.catalog import Product

pytestmark = pytest.mark.asyncio(loop_scope="session")


class _Obj:
    def __init__(self, name):
        self.object_name = name


class _Resp:
    def __init__(self, data):
        self._data = data

    def read(self):
        return self._data

    def close(self):
        pass

    def release_conn(self):
        pass


class _FakeMinio:
    """Minimal stand-in for minio.Minio backed by a {key: bytes} dict."""

    def __init__(self, tree):
        self.tree = tree

    def list_objects(self, bucket, prefix="", recursive=True):
        return [_Obj(k) for k in self.tree if k.startswith(prefix)]

    def get_object(self, bucket, key):
        return _Resp(self.tree[key])


async def test_import_maps_sku_folders_into_media_and_db(
    _sessionmaker, monkeypatch, tmp_path
):
    monkeypatch.setattr(settings, "media_root", str(tmp_path))
    monkeypatch.setattr(settings, "media_url_prefix", "/media")
    monkeypatch.setattr(settings, "minio_bucket", "photos")

    async with _sessionmaker() as db:
        db.add(Product(name="Ring 2000", sku="2000"))  # has a folder
        db.add(Product(name="Ring 3000", sku="3000"))  # no folder → skipped
        await db.commit()

    fake = _FakeMinio(
        {
            "2000/b.png": b"two",       # out-of-order + shows sorting
            "2000/a.jpg": b"one",
            "2000/notes.txt": b"skip",  # non-image → filtered out
            "9999/x.jpg": b"orphan",    # no matching product → ignored
        }
    )

    summary = await mod.import_product_images(client=fake)

    assert summary == {"products": 2, "photos": 2, "skipped": ["3000"]}

    # Files landed under media_root/products/{sku}/ with the real bytes.
    assert (tmp_path / "products/2000/a.jpg").read_bytes() == b"one"
    assert (tmp_path / "products/2000/b.png").read_bytes() == b"two"
    assert not (tmp_path / "products/2000/notes.txt").exists()  # filtered

    async with _sessionmaker() as db:
        p = (
            await db.execute(select(Product).where(Product.sku == "2000"))
        ).scalar_one()
        assert p.images == [
            "/media/products/2000/a.jpg",
            "/media/products/2000/b.png",
        ]  # sorted, image-only
        assert p.image_url == "/media/products/2000/a.jpg"  # first = primary

        empty = (
            await db.execute(select(Product).where(Product.sku == "3000"))
        ).scalar_one()
        assert empty.images == []  # no folder → untouched
        assert empty.image_url is None


async def test_make_client_errors_when_unconfigured(monkeypatch):
    for k in ("minio_endpoint", "minio_access_key", "minio_secret_key", "minio_bucket"):
        monkeypatch.setattr(settings, k, "")
    with pytest.raises(RuntimeError, match="MinIO is not configured"):
        mod._make_client()
