"""Runnable checks for the validation most likely to break silently: phone format
and province membership. These mirror the client Zod rules (server is the truth).
No DB required.

Run: pytest   — or:  python -m tests.test_orders   (framework-free smoke check)

Order idempotency (unique key + router dedup) is an integration concern; it's
verified end-to-end via docker-compose (see README / plan §8), not mocked here.
"""

import pytest
from pydantic import ValidationError

from app.domains.orders import OrderCreate


def _payload(**over):
    base = dict(
        full_name="Ali Rezaei",
        phone="09121234567",
        store_name="Rezaei Jewelry",
        province="Tehran",
        items=[{"quantity": 2}],
    )
    base.update(over)
    return base


def test_phone_valid():
    assert OrderCreate(**_payload()).phone == "09121234567"


@pytest.mark.parametrize(
    "bad", ["0912123456", "9121234567", "+989121234567", "08121234567", "abcd", ""]
)
def test_phone_invalid(bad):
    with pytest.raises(ValidationError):
        OrderCreate(**_payload(phone=bad))


def test_province_must_be_in_list():
    with pytest.raises(ValidationError):
        OrderCreate(**_payload(province="Atlantis"))


def test_requires_at_least_one_item():
    with pytest.raises(ValidationError):
        OrderCreate(**_payload(items=[]))


# ---- Guest checkout + phone-linked accounts ----
_asyncio = pytest.mark.asyncio(loop_scope="session")


async def _login(client, phone):
    r = await client.post("/api/v1/account/otp/request", json={"phone": phone})
    code = r.json()["dev_code"]
    await client.post("/api/v1/account/otp/verify", json={"phone": phone, "code": code})


@_asyncio
async def test_guest_can_order(client, order_payload):
    r = await client.post("/api/v1/orders", json=order_payload())
    assert r.status_code == 201, r.text
    assert r.json()["reference"].startswith("DG-")


@_asyncio
async def test_guest_order_claimed_after_otp_login(client, order_payload):
    # Guest orders with a phone; OTP login with that phone shows the order.
    phone = "09127777777"
    r = await client.post("/api/v1/orders", json=order_payload(phone=phone))
    ref = r.json()["reference"]
    await _login(client, phone)
    orders = (await client.get("/api/v1/account/me/orders")).json()
    assert ref in [o["reference"] for o in orders]


@_asyncio
async def test_guest_order_registers_customer(client, admin_client, order_payload):
    # A guest order auto-creates a Customer (identity = phone) in the admin panel.
    phone = "09126666666"
    r = await client.post("/api/v1/orders", json=order_payload(phone=phone))
    assert r.status_code == 201, r.text
    customers = (await admin_client.get("/api/v1/admin/customers")).json()
    match = [c for c in customers if c["phone"] == phone]
    assert match and match[0]["full_name"] == "Ali Rezaei"


@_asyncio
async def test_logged_in_order_binds_session_phone(client, order_payload):
    # A session phone overrides whatever the client sends in the payload.
    await _login(client, "09128888888")
    r = await client.post("/api/v1/orders", json=order_payload(phone="09120000001"))
    assert r.status_code == 201, r.text
    orders = (await client.get("/api/v1/account/me/orders")).json()
    assert r.json()["reference"] in [o["reference"] for o in orders]


if __name__ == "__main__":
    assert OrderCreate(**_payload()).phone == "09121234567"
    for bad in ["0912123456", "9121234567", "+989121234567"]:
        try:
            OrderCreate(**_payload(phone=bad))
        except ValidationError:
            continue
        raise AssertionError(f"expected {bad!r} to be rejected")
    try:
        OrderCreate(**_payload(province="Atlantis"))
    except ValidationError:
        pass
    else:
        raise AssertionError("expected invalid province to be rejected")
    print("ok: phone + province validation")
