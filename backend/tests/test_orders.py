"""Runnable checks for the validation most likely to break silently: phone format
and province membership. These mirror the client Zod rules (server is the truth).
No DB required.

Run: pytest   — or:  python -m tests.test_orders   (framework-free smoke check)

Order idempotency (unique key + router dedup) is an integration concern; it's
verified end-to-end via docker-compose (see README / plan §8), not mocked here.
"""

import pytest
from pydantic import ValidationError

from app.schemas.order import OrderCreate


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
