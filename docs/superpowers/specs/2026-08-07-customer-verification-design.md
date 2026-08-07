# Customer Business-License Verification — Design

**Date:** 2026-08-07
**Status:** Approved (brainstorming)

## Problem

Shop orders are currently account-less: anyone can `POST /orders` without logging
in. We want customers to upload their business-license documents, have an admin
review and approve/reject them, and **block unapproved customers from placing
orders**. On approval (and rejection) the customer gets an SMS.

## Decisions

- **Order gating:** to place an order a customer must be logged in **and**
  `approved`. Guest checkout is removed. Account-less order *tracking*
  (`/orders/track`) stays for legacy orders.
- **Status model:** `unverified | pending | approved | rejected` (+ optional
  rejection reason).
- **Documents:** multiple files, images + PDF, stored as a JSONB list on the
  customer.
- **SMS:** on `approved` and on `rejected` (reason included). Reuses the existing
  `send_sms(to, message)` helper.

## Data model — `customers` table (migration 0008)

| Column | Type | Notes |
|---|---|---|
| `verification_status` | enum `customer_verification_status` | `unverified`/`pending`/`approved`/`rejected`, default `unverified`, not null |
| `verification_documents` | JSONB | list of `{url, filename, uploaded_at}`, default `[]` |
| `rejection_reason` | String(300), nullable | admin note, shown back to the customer |
| `verified_at` | DateTime(tz), nullable | set when approved |

New enum `CustomerVerificationStatus(StrEnum)` in `app/models/customer.py`
(mirrors the `OrderStatus` pattern).

**State flow:** `unverified` → (first doc uploaded) `pending` → admin →
`approved` | `rejected`. A `rejected` customer re-uploading returns to `pending`.

*Rationale for JSONB over a table:* docs are always read/written as a set with
the customer and reviewed as a whole (like landing `content`). A dedicated
`customer_documents` table is the upgrade path if per-doc workflow is ever needed.

## Backend endpoints

### Customer (`app/api/v1/account.py`, `require_customer`)
- `POST /account/me/documents` — multipart upload. Allowed `image/*` +
  `application/pdf`; ~10 MB cap; max 5 files total. Appends `{url, filename,
  uploaded_at}` to `verification_documents`. If status is `unverified` or
  `rejected`, flips to `pending` and clears `rejection_reason`. Reuses
  `get_storage()`.
- `DELETE /account/me/documents/{idx}` — remove a doc while `pending` (fix a bad
  scan). 400 if not `pending`.
- `CustomerOut` gains `verification_status`, `verification_documents`,
  `rejection_reason` — same shape feeds the account page and the admin view.

### Admin (new `app/api/v1/admin_customers.py`, `require_admin`)
- `GET /admin/customers?status=<optional>` — review queue (list).
- `GET /admin/customers/{id}` — detail incl. document URLs.
- `PATCH /admin/customers/{id}/verification` — body `{status, reason?}` where
  status ∈ `approved`/`rejected`.
  - `approved`: set `verified_at`, clear `rejection_reason`, SMS
    `"احراز هویت شما با موفقیت انجام شد"`.
  - `rejected`: store `reason`, SMS the reason so the customer knows to re-submit.
  - No-op if the status is unchanged.

Register the new router in `app/api/v1/__init__.py` / `app/main.py` alongside the
other admin routers.

## Order gating (the pivot)

`POST /orders` in `app/api/v1/public.py`:
- Add `require_customer`. Guest checkout removed.
- Guard: `customer.verification_status == approved` else **403**.
- Bind `phone` from the session customer (ignore client-supplied phone) so orders
  can't be spoofed to another number. `full_name`/`store_name`/`province`/`city`/
  `note` still come from the form.
- `/orders/track` (account-less lookup by reference+phone) is unchanged.

## Frontend

- **`pages/account/verification.vue`** — status badge, upload UI (new
  `composables/useCustomerUpload.ts`, mirrors `useAdminUpload` but hits
  `/account/me/documents`), list of uploaded docs with remove, rejection reason
  when present. Linked from `pages/account/index.vue` with a status badge.
- **Shop order form** (`pages/shop`, order submit path) — if not logged in →
  login; if logged in but not `approved` → block submit and show a "complete
  verification" CTA linking to `/account/verification`. Backend 403 is the
  hard enforcement; this is UX.
- **`pages/admin/customers/index.vue`** — review queue: list, filter by status
  (default pending), open a customer to view documents, approve/reject with an
  optional reason. New entry in the admin nav.

## Testing

One integration test (async, real PostgreSQL, matching existing suite):
1. Customer uploads a doc → status `pending`.
2. `POST /orders` returns **403** while not `approved`.
3. Admin `PATCH .../verification` → `approved`; assert SMS stub logged the success
   text and `verified_at` set.
4. `POST /orders` now returns **201**.

## Out of scope / upgrade paths

- Per-document review states (approve individual files) — table upgrade if needed.
- Document expiry / re-verification cadence.
- S3 storage (already the documented upgrade path in `storage.py`).
