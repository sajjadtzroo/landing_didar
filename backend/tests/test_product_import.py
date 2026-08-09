"""Bulk CSV product import: upsert by SKU, background job, per-row errors."""

import asyncio

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

IMPORT = "/api/v1/admin/products/import"
TEMPLATE = "/api/v1/admin/products/import/template"
PRODUCTS = "/api/v1/admin/products"


def _csv(*lines: str) -> bytes:
    header = "sku,name,slug,description,weight_grams,karat,ojrat_percent,category,supplier,product_status,warrantable,is_active,sort_order"
    return ("\n".join([header, *lines])).encode("utf-8")


async def _upload(admin_client, data: bytes, sync_images=False):
    return await admin_client.post(
        IMPORT,
        files={"file": ("products.csv", data, "text/csv")},
        data={"sync_images": "true" if sync_images else "false"},
    )


async def _wait_job(admin_client, job_id: str, tries=50):
    for _ in range(tries):
        job = (await admin_client.get(f"{IMPORT}/{job_id}")).json()
        if job["status"] in ("done", "failed"):
            return job
        await asyncio.sleep(0.05)
    raise AssertionError(f"job stuck: {job}")


async def test_template_downloads(admin_client):
    r = await admin_client.get(TEMPLATE)
    assert r.status_code == 200
    assert r.text.splitlines()[0].startswith("sku,name")


async def test_import_creates_and_updates_by_sku(admin_client):
    # 1st import: create two products
    r = await _upload(admin_client, _csv(
        "BULK-1,انگشتر بالک,,توضیح,4.5,18,7,daily,کارگاه غرب,sellable,true,true,1",
        "BULK-2,گردنبند بالک,,,12,18,8,لوکس,,نمونه,بله,true,2",
    ))
    assert r.status_code == 202, r.text
    job = await _wait_job(admin_client, r.json()["job_id"])
    assert job["status"] == "done"
    assert job["created_count"] == 2 and job["updated_count"] == 0

    listed = {p["sku"]: p for p in (await admin_client.get(PRODUCTS)).json()}
    assert listed["BULK-1"]["supplier"] == "کارگاه غرب"
    # Persian labels normalized:
    assert listed["BULK-2"]["category"] == "luxury"
    assert listed["BULK-2"]["product_status"] == "sample"

    # 2nd import: same SKU updates, blank cells leave fields unchanged
    r2 = await _upload(admin_client, _csv("BULK-1,انگشتر بالک ۲,,,5.0,,,,,,,,"))
    job2 = await _wait_job(admin_client, r2.json()["job_id"])
    assert job2["created_count"] == 0 and job2["updated_count"] == 1
    p1 = {p["sku"]: p for p in (await admin_client.get(PRODUCTS)).json()}["BULK-1"]
    assert p1["name"] == "انگشتر بالک ۲"
    assert float(p1["weight_grams"]) == 5.0
    assert p1["supplier"] == "کارگاه غرب"  # blank cell → unchanged


async def test_bad_rows_reported_good_rows_land(admin_client):
    r = await _upload(admin_client, _csv(
        "OK-1,محصول سالم,,,3,18,5,daily,,sellable,true,true,0",
        ",بدون کد,,,3,18,5,daily,,sellable,true,true,0",       # missing sku
        "BAD-2,عیار بد,,,3,99,5,daily,,sellable,true,true,0",  # karat out of range
    ))
    job = await _wait_job(admin_client, r.json()["job_id"])
    assert job["status"] == "done"
    assert job["created_count"] == 1
    assert len(job["errors"]) == 2
    assert {e["row"] for e in job["errors"]} == {3, 4}


async def test_persian_digits_and_bom(admin_client):
    body = "﻿" + "sku,name,weight_grams,karat\nFA-1,محصول فارسی,۱۲٫۵,۱۸"
    r = await _upload(admin_client, body.encode("utf-8"))
    job = await _wait_job(admin_client, r.json()["job_id"])
    assert job["status"] == "done" and job["created_count"] == 1
    p = {p["sku"]: p for p in (await admin_client.get(PRODUCTS)).json()}["FA-1"]
    assert float(p["weight_grams"]) == 12.5 and p["karat"] == 18


async def test_missing_required_header_422(admin_client):
    r = await _upload(admin_client, b"name,weight\nx,1")
    assert r.status_code == 422


async def test_import_requires_admin(client):
    r = await client.get(TEMPLATE)
    assert r.status_code == 401
