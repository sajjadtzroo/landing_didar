# Customer Business-License Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Customers register (phone-OTP), provide business info, and upload license documents; an admin approves/rejects them; only `approved` customers can place orders; approval/rejection fires an SMS.

**Architecture:** Extend the existing `customers` table with a verification status enum, a JSONB document list, and profile fields. Customer-facing upload endpoints live in `account.py`; a new admin router reviews and sets status (reusing `send_sms`). `POST /orders` gains `require_customer` + an `approved` guard and binds phone from the session. Frontend adds a verification/registration page, an admin review page, and an order-form guard.

**Tech Stack:** FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL (JSONB + enum), Pydantic v2, Nuxt 3 / Vue 3, pytest-asyncio.

## Global Constraints

- Python line length ≤ 88 (ruff). Match existing style.
- All backend I/O is async; DB via `AsyncSession` from `get_db`.
- SMS goes through `app.services.sms.send_sms(to, message)` (logs in dev/tests when no creds).
- Persian (RTL) user-facing copy, matching existing strings.
- Migrations are hand-written under `alembic/versions/`, sequential id after `0007`.
- Enum values are lowercase strings; StrEnum pattern mirrors `OrderStatus`.
- JSONB columns must be **reassigned** (not mutated in place) so SQLAlchemy flags the change.
- New admin router is guarded by `require_admin`; customer routes by `require_customer`.

---

### Task 1: Data model + migration + read schema

**Files:**
- Modify: `backend/app/models/customer.py`
- Create: `backend/alembic/versions/0008_customer_verification.py`
- Modify: `backend/app/schemas/customer.py`
- Test: `backend/tests/test_account.py`

**Interfaces:**
- Produces: `CustomerVerificationStatus` StrEnum (`unverified|pending|approved|rejected`); `Customer` columns `verification_status`, `verification_documents` (list[dict]), `rejection_reason` (str|None), `verified_at` (datetime|None), `store_name` (str|None); `CustomerOut` now returns those fields; `CustomerUpdate` accepts optional `store_name`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_account.py` (uses the existing `_login` helper):

```python
async def test_new_customer_is_unverified_with_no_docs(client):
    cust = await _login(client, "09120000010")
    assert cust["verification_status"] == "unverified"
    assert cust["verification_documents"] == []
    assert cust["rejection_reason"] is None
    assert cust["store_name"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_account.py::test_new_customer_is_unverified_with_no_docs -v`
Expected: FAIL — `KeyError: 'verification_status'` (field not in `CustomerOut`).

- [ ] **Step 3: Extend the model**

In `backend/app/models/customer.py` add imports and columns. At top, add to the sqlalchemy import block `Enum as SAEnum` and `import enum`, `from datetime import datetime`, and `from sqlalchemy.dialects.postgresql import JSONB` (UUID already imported from there — extend that line). Add the enum above `class Customer`:

```python
class CustomerVerificationStatus(enum.StrEnum):
    unverified = "unverified"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
```

Inside `class Customer`, after `full_name`:

```python
    store_name: Mapped[str | None] = mapped_column(String(80))
    verification_status: Mapped[CustomerVerificationStatus] = mapped_column(
        SAEnum(CustomerVerificationStatus, name="customer_verification_status"),
        default=CustomerVerificationStatus.unverified,
        nullable=False,
    )
    verification_documents: Mapped[list] = mapped_column(
        JSONB, default=list, nullable=False
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(300))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

- [ ] **Step 4: Write the migration**

Create `backend/alembic/versions/0008_customer_verification.py`:

```python
"""add customer verification fields

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-07
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

_STATUS = postgresql.ENUM(
    "unverified", "pending", "approved", "rejected",
    name="customer_verification_status",
)


def upgrade() -> None:
    _STATUS.create(op.get_bind(), checkfirst=True)
    op.add_column("customers", sa.Column("store_name", sa.String(80)))
    op.add_column(
        "customers",
        sa.Column(
            "verification_status", _STATUS,
            nullable=False, server_default="unverified",
        ),
    )
    op.add_column(
        "customers",
        sa.Column(
            "verification_documents", postgresql.JSONB(),
            nullable=False, server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("customers", sa.Column("rejection_reason", sa.String(300)))
    op.add_column(
        "customers", sa.Column("verified_at", sa.DateTime(timezone=True))
    )


def downgrade() -> None:
    op.drop_column("customers", "verified_at")
    op.drop_column("customers", "rejection_reason")
    op.drop_column("customers", "verification_documents")
    op.drop_column("customers", "verification_status")
    op.drop_column("customers", "store_name")
    _STATUS.drop(op.get_bind(), checkfirst=True)
```

- [ ] **Step 5: Extend the schemas**

In `backend/app/schemas/customer.py`, replace `CustomerOut` and `CustomerUpdate`:

```python
class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    phone: str
    full_name: str | None
    store_name: str | None
    verification_status: str
    verification_documents: list[dict]
    rejection_reason: str | None


class CustomerUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=60)
    store_name: str | None = Field(default=None, max_length=80)
```

Then in `backend/app/api/v1/account.py`, update `update_me` to also set `store_name`:

```python
    c.full_name = payload.full_name
    c.store_name = payload.store_name
```

- [ ] **Step 6: Recreate the test DB and run the test**

The test DB is created from models/migrations by conftest. Run:
`cd backend && pytest tests/test_account.py::test_new_customer_is_unverified_with_no_docs -v`
Expected: PASS. If it errors on a stale schema, drop the test DB (conftest `_ensure_test_db` recreates it) and re-run.

- [ ] **Step 7: Run the full account suite (nothing regressed)**

Run: `cd backend && pytest tests/test_account.py -v`
Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/customer.py backend/alembic/versions/0008_customer_verification.py backend/app/schemas/customer.py backend/app/api/v1/account.py backend/tests/test_account.py
git commit -m "feat(customer): verification status + docs + store_name schema/migration

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Customer document upload / delete endpoints

**Files:**
- Modify: `backend/app/api/v1/account.py`
- Test: `backend/tests/test_account.py`

**Interfaces:**
- Consumes: `CustomerVerificationStatus`, `get_storage()`, `_current()`.
- Produces: `POST /api/v1/account/me/documents` (multipart `file`) → `CustomerOut`; `DELETE /api/v1/account/me/documents/{idx}` → `CustomerOut`. First upload from `unverified`/`rejected` sets status `pending` and clears `rejection_reason`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_account.py`:

```python
async def test_upload_document_sets_pending(client):
    await _login(client, "09120000011")
    r = await client.post(
        f"{ACC}/me/documents",
        files={"file": ("license.png", b"\x89PNG_fake", "image/png")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["verification_status"] == "pending"
    assert len(body["verification_documents"]) == 1
    assert body["verification_documents"][0]["url"].startswith("/media/")

async def test_reject_unsupported_document_type(client):
    await _login(client, "09120000012")
    r = await client.post(
        f"{ACC}/me/documents",
        files={"file": ("x.txt", b"nope", "text/plain")},
    )
    assert r.status_code == 415

async def test_delete_document_while_pending(client):
    await _login(client, "09120000013")
    await client.post(
        f"{ACC}/me/documents",
        files={"file": ("l.png", b"x", "image/png")},
    )
    r = await client.delete(f"{ACC}/me/documents/0")
    assert r.status_code == 200
    assert r.json()["verification_documents"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_account.py -k document -v`
Expected: FAIL with 404/405 (routes not defined).

- [ ] **Step 3: Implement the endpoints**

In `backend/app/api/v1/account.py`: extend imports —
`from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile`,
`from datetime import UTC, datetime, timedelta` (UTC/datetime already imported — keep),
`from app.models.customer import ..., CustomerVerificationStatus` (extend existing import),
`from app.services.storage import get_storage`.

Add near the OTP constants:

```python
_ALLOWED_DOC = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
_MAX_DOC_BYTES = 10 * 1024 * 1024  # 10 MB
_MAX_DOCS = 5
```

Add the endpoints (after `update_me`):

```python
@router.post("/me/documents", response_model=CustomerOut)
async def upload_document(
    file: UploadFile = File(...),
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in _ALLOWED_DOC:
        raise HTTPException(415, detail="فرمت فایل پشتیبانی نمی‌شود")
    c = await _current(db, customer_id)
    if len(c.verification_documents) >= _MAX_DOCS:
        raise HTTPException(400, detail="حداکثر تعداد مدارک بارگذاری شده است")
    data = await file.read()
    if len(data) > _MAX_DOC_BYTES:
        raise HTTPException(413, detail="حجم فایل زیاد است (حداکثر ۱۰ مگابایت)")
    url = await get_storage().save(file.filename or "document", data)
    # reassign (not append) so SQLAlchemy flags the JSONB change
    c.verification_documents = [
        *c.verification_documents,
        {
            "url": url,
            "filename": file.filename,
            "uploaded_at": datetime.now(UTC).isoformat(),
        },
    ]
    if c.verification_status in (
        CustomerVerificationStatus.unverified,
        CustomerVerificationStatus.rejected,
    ):
        c.verification_status = CustomerVerificationStatus.pending
        c.rejection_reason = None
    await db.commit()
    await db.refresh(c)
    return c


@router.delete("/me/documents/{idx}", response_model=CustomerOut)
async def delete_document(
    idx: int,
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    c = await _current(db, customer_id)
    if c.verification_status != CustomerVerificationStatus.pending:
        raise HTTPException(400, detail="فقط در وضعیت در انتظار بررسی قابل حذف است")
    if idx < 0 or idx >= len(c.verification_documents):
        raise HTTPException(404, detail="مدرک یافت نشد")
    docs = list(c.verification_documents)
    docs.pop(idx)
    c.verification_documents = docs
    await db.commit()
    await db.refresh(c)
    return c
```

- [ ] **Step 4: Run the tests**

Run: `cd backend && pytest tests/test_account.py -k document -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/account.py backend/tests/test_account.py
git commit -m "feat(account): business-license document upload/delete → pending

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Admin verification router (list / detail / approve-reject + SMS)

**Files:**
- Create: `backend/app/api/v1/admin_customers.py`
- Modify: `backend/app/schemas/customer.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_admin_customers.py`

**Interfaces:**
- Consumes: `require_admin`, `send_sms`, `Customer`, `CustomerVerificationStatus`.
- Produces: `GET /api/v1/admin/customers?status=` → `list[CustomerAdminOut]`; `GET /api/v1/admin/customers/{id}` → `CustomerAdminOut`; `PATCH /api/v1/admin/customers/{id}/verification` body `{status, reason?}` → `CustomerAdminOut`. On `approved`: sets `verified_at`, clears reason, SMS success text. On `rejected`: stores `reason`, SMS the reason.

- [ ] **Step 1: Add schemas**

In `backend/app/schemas/customer.py` add:

```python
from datetime import datetime  # add to imports at top


class CustomerAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    phone: str
    full_name: str | None
    store_name: str | None
    verification_status: str
    verification_documents: list[dict]
    rejection_reason: str | None
    verified_at: datetime | None
    created_at: datetime


class VerificationUpdate(BaseModel):
    status: str  # "approved" | "rejected"
    reason: str | None = Field(default=None, max_length=300)

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        if v not in ("approved", "rejected"):
            raise ValueError("status must be approved or rejected")
        return v
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_admin_customers.py`:

```python
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

ACC = "/api/v1/account"
ADM = "/api/v1/admin/customers"


async def _login(client, phone):
    r = await client.post(f"{ACC}/otp/request", json={"phone": phone})
    code = r.json()["dev_code"]
    await client.post(f"{ACC}/otp/verify", json={"phone": phone, "code": code})


async def _submit_docs(client, phone):
    await _login(client, phone)
    await client.post(
        f"{ACC}/me/documents",
        files={"file": ("l.png", b"x", "image/png")},
    )


async def test_admin_lists_pending_customers(client, admin_client):
    await _submit_docs(client, "09120000021")
    r = await admin_client.get(f"{ADM}?status=pending")
    assert r.status_code == 200
    assert any(c["phone"] == "09120000021" for c in r.json())


async def test_admin_approve_sets_status_and_sms(client, admin_client, caplog):
    await _submit_docs(client, "09120000022")
    cid = (await client.get(f"{ACC}/me")).json()["id"]
    import logging
    with caplog.at_level(logging.INFO):
        r = await admin_client.patch(
            f"{ADM}/{cid}/verification", json={"status": "approved"}
        )
    assert r.status_code == 200
    assert r.json()["verification_status"] == "approved"
    assert r.json()["verified_at"] is not None
    assert "احراز هویت شما با موفقیت انجام شد" in caplog.text


async def test_admin_reject_stores_reason(client, admin_client):
    await _submit_docs(client, "09120000023")
    cid = (await client.get(f"{ACC}/me")).json()["id"]
    r = await admin_client.patch(
        f"{ADM}/{cid}/verification",
        json={"status": "rejected", "reason": "مدرک ناخواناست"},
    )
    assert r.status_code == 200
    assert r.json()["verification_status"] == "rejected"
    assert r.json()["rejection_reason"] == "مدرک ناخواناست"
```

Note: SMS stub logs via loguru. If `caplog` does not capture loguru in this project, assert on `r.json()` only and drop the caplog assertion — check `test_sms.py`/`test_notifications.py` for the project's logging-capture pattern and mirror it.

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && pytest tests/test_admin_customers.py -v`
Expected: FAIL — 404 (router not registered).

- [ ] **Step 4: Implement the router**

Create `backend/app/api/v1/admin_customers.py`:

```python
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.db import get_db
from app.models.customer import Customer, CustomerVerificationStatus
from app.schemas.customer import CustomerAdminOut, VerificationUpdate
from app.services.sms import send_sms

router = APIRouter(dependencies=[Depends(require_admin)])

APPROVED_SMS = "احراز هویت شما با موفقیت انجام شد."


@router.get("/customers", response_model=list[CustomerAdminOut])
async def list_customers(
    status: str | None = None, db: AsyncSession = Depends(get_db)
):
    q = select(Customer).order_by(Customer.created_at.desc())
    if status:
        q = q.where(Customer.verification_status == status)
    return (await db.execute(q)).scalars().all()


@router.get("/customers/{customer_id}", response_model=CustomerAdminOut)
async def get_customer(
    customer_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    c = await db.get(Customer, customer_id)
    if c is None:
        raise HTTPException(404, detail="مشتری یافت نشد")
    return c


@router.patch(
    "/customers/{customer_id}/verification", response_model=CustomerAdminOut
)
async def set_verification(
    customer_id: uuid.UUID,
    payload: VerificationUpdate,
    db: AsyncSession = Depends(get_db),
):
    c = await db.get(Customer, customer_id)
    if c is None:
        raise HTTPException(404, detail="مشتری یافت نشد")
    new = CustomerVerificationStatus(payload.status)
    if c.verification_status == new:
        return c
    c.verification_status = new
    if new == CustomerVerificationStatus.approved:
        c.verified_at = datetime.now(UTC)
        c.rejection_reason = None
        await send_sms(c.phone, APPROVED_SMS)
    else:  # rejected
        c.rejection_reason = payload.reason
        await send_sms(
            c.phone, f"مدارک شما تایید نشد. {payload.reason or ''}".strip()
        )
    await db.commit()
    await db.refresh(c)
    return c
```

- [ ] **Step 5: Register the router**

In `backend/app/main.py`: add `admin_customers` to the `from app.api.v1 import (...)` block, and after the `admin_stats` include:

```python
app.include_router(
    admin_customers.router, prefix=f"{API}/admin", tags=["admin:customers"]
)
```

- [ ] **Step 6: Run the tests**

Run: `cd backend && pytest tests/test_admin_customers.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/v1/admin_customers.py backend/app/schemas/customer.py backend/app/main.py backend/tests/test_admin_customers.py
git commit -m "feat(admin): customer verification review + approve/reject SMS

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Gate order creation on an approved customer

**Files:**
- Modify: `backend/app/api/v1/public.py` (`create_order`, ~line 206)
- Modify: `backend/tests/conftest.py` (add an approved-buyer helper)
- Modify: `backend/tests/test_admin_orders.py`, `backend/tests/test_admin_stats.py`, `backend/tests/test_account.py` (existing order-creation calls now need an approved session)
- Test: `backend/tests/test_orders.py` (new gating tests)

**Interfaces:**
- Consumes: `require_customer`, `Customer`, `CustomerVerificationStatus`.
- Produces: `POST /api/v1/orders` requires a logged-in customer whose `verification_status == approved` (else 403). Order `phone` is bound from the session customer, ignoring the client value.

- [ ] **Step 1: Add an approved-buyer fixture to conftest**

In `backend/tests/conftest.py` add (uses `_sessionmaker`):

```python
@pytest_asyncio.fixture
async def approved_client(_sessionmaker):
    """A logged-in customer who has been admin-approved (can place orders)."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app
    from app.models.customer import Customer, CustomerVerificationStatus

    phone = "09129999999"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/v1/account/otp/request", json={"phone": phone})
        code = r.json()["dev_code"]
        await c.post(
            "/api/v1/account/otp/verify", json={"phone": phone, "code": code}
        )
        async with _sessionmaker() as db:
            cust = (
                await db.execute(
                    __import__("sqlalchemy").select(Customer).where(
                        Customer.phone == phone
                    )
                )
            ).scalar_one()
            cust.verification_status = CustomerVerificationStatus.approved
            await db.commit()
        yield c
```

(If the project already imports `select` at the top of conftest, use it instead of the `__import__` inline.)

- [ ] **Step 2: Write the failing gating tests**

Add to `backend/tests/test_orders.py`:

```python
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _login(client, phone):
    r = await client.post("/api/v1/account/otp/request", json={"phone": phone})
    code = r.json()["dev_code"]
    await client.post(
        "/api/v1/account/otp/verify", json={"phone": phone, "code": code}
    )


async def test_order_requires_login(client, order_payload):
    r = await client.post("/api/v1/orders", json=order_payload())
    assert r.status_code == 401


async def test_order_blocked_when_not_approved(client, order_payload):
    await _login(client, "09128888888")
    r = await client.post("/api/v1/orders", json=order_payload())
    assert r.status_code == 403


async def test_order_allowed_when_approved(approved_client, order_payload):
    r = await approved_client.post("/api/v1/orders", json=order_payload())
    assert r.status_code == 201
    # phone is bound from the session, not the payload
    assert r.json()["reference"].startswith("DG-")
```

- [ ] **Step 3: Run to verify they fail**

Run: `cd backend && pytest tests/test_orders.py -k "requires_login or not_approved or when_approved" -v`
Expected: FAIL (currently returns 201 with no auth).

- [ ] **Step 4: Implement the guard**

In `backend/app/api/v1/public.py`, extend imports:
`from app.api.deps import get_client_ip, require_customer` (extend the existing deps import),
`from app.models.customer import Customer, CustomerVerificationStatus`.

In `create_order`, add the dependency parameter and guard at the top of the function body (before the honeypot/idempotency logic), then bind phone:

```python
async def create_order(
    request: Request,
    payload: OrderCreate,
    background: BackgroundTasks,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    customer_id: uuid.UUID = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(401, detail="Not authenticated")
    if customer.verification_status != CustomerVerificationStatus.approved:
        raise HTTPException(403, detail="حساب شما هنوز تأیید نشده است")
    # bind phone from the verified session — never trust the client value
    payload.phone = customer.phone
    ...  # existing honeypot / idempotency / create_order body unchanged
```

Match the existing signature order/params of `create_order` (keep whatever params it already declares; only add `customer_id`). Keep the honeypot early-return **after** the guard is fine, or before — order doesn't matter, but the auth guard must run for real submissions.

- [ ] **Step 5: Fix existing order-creation tests**

These call `POST /api/v1/orders` unauthenticated and will now 401/403. Update each to use `approved_client` instead of `client` for the order-creation call:

- `backend/tests/test_admin_orders.py:11` — the setup helper that posts an order. Change its client parameter to `approved_client` (thread the fixture through the tests that use it).
- `backend/tests/test_admin_stats.py:30` — same: create seed orders via `approved_client`.
- `backend/tests/test_account.py:75` — the order-tracking / my-orders setup: log in + approve (reuse `approved_client`, or approve inline like the fixture) before posting.

For each: add `approved_client` to the test signature and replace the `client.post("/api/v1/orders", ...)` call with `approved_client.post(...)`. Note the bound phone is `09129999999`, so assertions that check the ordering phone must expect that value (or post with the matching phone).

- [ ] **Step 6: Run the full backend suite**

Run: `cd backend && pytest -q`
Expected: all PASS. Fix any test still posting orders unauthenticated by routing it through `approved_client`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/v1/public.py backend/tests/conftest.py backend/tests/test_orders.py backend/tests/test_admin_orders.py backend/tests/test_admin_stats.py backend/tests/test_account.py
git commit -m "feat(orders): require approved customer; bind phone from session

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Frontend — customer verification / registration page

**Files:**
- Modify: `frontend/types/index.ts` (extend `Customer`)
- Create: `frontend/composables/useCustomerUpload.ts`
- Create: `frontend/pages/account/verification.vue`
- Modify: `frontend/components/AccountShell.vue` (nav entry)

**Interfaces:**
- Consumes: `apiFetch`, `useCustomerAuth`, `CustomerOut` shape from Task 1.
- Produces: `useCustomerUpload().upload(file)` → updated `Customer`; a verification page at `/account/verification`.

- [ ] **Step 1: Extend the Customer type**

In `frontend/types/index.ts`, extend `interface Customer` (near line 80):

```typescript
export interface CustomerDocument {
  url: string
  filename: string | null
  uploaded_at: string
}

export interface Customer {
  id: string
  phone: string
  full_name: string | null
  store_name: string | null
  verification_status: 'unverified' | 'pending' | 'approved' | 'rejected'
  verification_documents: CustomerDocument[]
  rejection_reason: string | null
}
```

(Keep any existing fields already on `Customer`; add the new ones.)

- [ ] **Step 2: Upload composable**

Create `frontend/composables/useCustomerUpload.ts` (mirror `useAdminUpload.ts`, different endpoint, returns the updated customer):

```typescript
import type { Customer } from '~/types'

// Uploads a verification document; returns the updated customer.
export function useCustomerUpload() {
  async function upload(file: File): Promise<Customer> {
    const form = new FormData()
    form.append('file', file)
    return apiFetch<Customer>('/account/me/documents', {
      method: 'POST',
      body: form,
    })
  }
  async function remove(idx: number): Promise<Customer> {
    return apiFetch<Customer>(`/account/me/documents/${idx}`, {
      method: 'DELETE',
    })
  }
  return { upload, remove }
}
```

- [ ] **Step 3: Verification page**

Create `frontend/pages/account/verification.vue`. Requirements (follow the styling of existing `pages/account/profile.vue`):
- Wrap in `<AccountShell>` (same as other account pages).
- Show a status badge from `customer.verification_status` with Persian labels: `unverified` → «تأیید نشده», `pending` → «در انتظار بررسی», `approved` → «تأیید شده», `rejected` → «رد شده».
- If `rejected`, show `customer.rejection_reason` in a warning box.
- A profile mini-form (full_name, store_name) that PATCHes `/account/me` (reuse `useCustomerAuth` or `apiFetch`) — this is the "registration info" step.
- A file input (`accept="image/*,application/pdf"`). On change, call `useCustomerUpload().upload(file)`, then refresh the customer state (`useCustomerAuth().ensure(true)`).
- List `customer.verification_documents` with filename + a link to `url`; show a remove button that calls `useCustomerUpload().remove(idx)` when status is `pending`.
- Hide the upload input when `approved`.

Copy the page-scaffold (script setup + AccountShell + form styling) from `pages/account/profile.vue` so classes/layout match. Keep all user-facing strings Persian.

- [ ] **Step 4: Nav entry + status hint**

In `frontend/components/AccountShell.vue`, add to the `tabs` array (import a suitable lucide icon, e.g. `ShieldCheck`):

```typescript
  { to: '/account/verification', label: 'احراز هویت', icon: ShieldCheck },
```

- [ ] **Step 5: Manual verification**

Run backend + frontend (see `DEPLOY.md` / project run skill). Log in at `/account/login`, open `/account/verification`:
- Fill name + store, upload an image → badge flips to «در انتظار بررسی», the doc appears in the list.
- Confirm the delete button removes it.

- [ ] **Step 6: Commit**

```bash
git add frontend/types/index.ts frontend/composables/useCustomerUpload.ts frontend/pages/account/verification.vue frontend/components/AccountShell.vue
git commit -m "feat(account): verification page — profile info + document upload

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Frontend — admin customer review page

**Files:**
- Create: `frontend/pages/admin/customers/index.vue`
- Modify: `frontend/components/AdminSidebar.vue` (nav entry)

**Interfaces:**
- Consumes: `apiFetch`, admin endpoints from Task 3.
- Produces: an admin review page at `/admin/customers`.

- [ ] **Step 1: Sidebar entry**

In `frontend/components/AdminSidebar.vue`, add to the `links` array (import a lucide icon such as `ShieldCheck`), after the FAQs entry:

```typescript
  { to: '/admin/customers', label: 'احراز هویت مشتریان', icon: ShieldCheck },
```

- [ ] **Step 2: Review page**

Create `frontend/pages/admin/customers/index.vue`. Follow the structure of `pages/admin/orders/index.vue` (admin layout, `apiFetch`, `useAsyncData`). Requirements:
- Fetch `apiFetch('/admin/customers?status=pending')` by default; a filter control to switch status (pending/approved/rejected/all → omit param for all).
- Table/cards showing phone, full_name, store_name, status badge, and each document as a thumbnail/link (`verification_documents[].url`).
- Per row: «تأیید» and «رد» buttons. «رد» opens a small reason input. Both call
  `apiFetch('/admin/customers/{id}/verification', { method: 'PATCH', body: { status, reason } })`, then refresh the list.
- Use the same admin page chrome/`definePageMeta` layout as the other admin pages.

- [ ] **Step 3: Manual verification**

As admin, open `/admin/customers`, see the pending customer from Task 5, view the document, click «تأیید». Reload the customer account page → status shows «تأیید شده». Confirm the approval SMS is logged in the backend console (`[SMS stub] ... احراز هویت شما با موفقیت انجام شد`).

- [ ] **Step 4: Commit**

```bash
git add frontend/pages/admin/customers/index.vue frontend/components/AdminSidebar.vue
git commit -m "feat(admin): customer verification review page

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Frontend — gate the order form on approval

**Files:**
- Modify: `frontend/components/OrderForm.vue`

**Interfaces:**
- Consumes: `useCustomerAuth`, `Customer.verification_status`.

- [ ] **Step 1: Guard the form**

In `frontend/components/OrderForm.vue`:
- On setup, `const { customer, ensure } = useCustomerAuth(); await ensure()`.
- Compute `canOrder = customer.value?.verification_status === 'approved'`.
- If not logged in (`customer` null): replace the submit button with a CTA linking to `/account/login`.
- If logged in but not approved: disable submit and show a notice linking to `/account/verification` — «برای ثبت سفارش ابتدا احراز هویت خود را کامل کنید».
- The backend already 403s, so this is UX only. Keep the existing `submit` logic for the approved path (phone is now bound server-side, so the phone field can be prefilled read-only from `customer.phone` — optional).

- [ ] **Step 2: Manual verification**

- Logged out: order form shows the login CTA.
- Logged in + pending: submit disabled, verification notice shown.
- Logged in + approved: order submits, returns a reference.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/OrderForm.vue
git commit -m "feat(shop): gate order form on approved verification

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Notes for the implementer

- **Registration = OTP login.** The existing `/account/login` already creates the customer row (`unverified`). "Registration + provide information" is the profile mini-form on the verification page (Task 5, Step 3) plus document upload. No separate signup endpoint is needed.
- **JSONB gotcha:** always reassign `verification_documents` to a new list; never `.append()` in place, or SQLAlchemy won't persist it.
- **Existing order tests will break** the moment Task 4 lands — that's expected and handled in Task 4, Step 5. Don't skip it.
- **SMS in dev/tests** logs instead of sending (`send_sms` falls back to loguru), so no gateway creds are required to verify the flow.
