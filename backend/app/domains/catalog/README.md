# catalog

Products (the storefront's source of truth), admin CRUD + media upload, bulk
CSV import as a pollable background job, and MinIO photo sync. Follows the
canonical skeleton in `../CLAUDE.md`.

## Layout

| Path | What lives here |
|---|---|
| `models/product.py` | `Product` |
| `models/import_job.py` | `ImportJob` — pollable progress row for background imports |
| `schemas/` | `ProductOut` / `AdminProductOut` / `ProductCreate` / `ProductUpdate`, `ImportJobOut` |
| `queries/product_query.py` | `ProductQuery` — admin list, active-catalog paging, slug lookup |
| `queries/import_job_query.py` | `ImportJobQuery` — job polling lookups |
| `actions/product_action.py` | `ProductAction` — create/update/delete/set_image |
| `actions/import_job_action.py` | `ImportJobAction` — creates the job rows the workers report into |
| `routers/public.py` | `/products` (cached JSON body) + `/products/{slug}` |
| `routers/admin.py` | product CRUD, media upload, CSV import + image-sync jobs |
| `services/import_service.py` | CSV parse/template + the background import/sync workers |
| `services/minio_import.py` | MinIO `{sku}/` photo-folder sync into local media |

## Routes

Public: `GET /products` (optional `page`/`page_size`, `X-Total-Count` header),
`GET /products/{slug}`. Admin: `GET/POST /admin/products`,
`PATCH/DELETE /admin/products/{id}`, `POST /admin/products/{id}/image`,
`POST /admin/media`, `GET /admin/products/import/template`,
`POST /admin/products/import` (+ `GET .../{job_id}` poll),
`POST /admin/products/sync-images`.

## Invariants & gotchas

- **Registration order**: orders' public router serves `/products/best-sellers`
  and must be registered BEFORE this domain's public router in `app/main.py`,
  or `/products/{slug}` swallows it.
- Public list caches the **finished JSON body** (not ORM rows) per
  `page`/`page_size` for 60s — re-serializing 500+ rows per hit was the
  measured hot-path ceiling (docs/perf/capacity-2026-08-12.md).
- "Active" means `is_active AND product_status != 'not_for_sale'` — one
  definition, in `ProductQuery._ACTIVE`.
- Bulk import: upsert by SKU; blank cell = "leave unchanged" on update;
  Persian digits/labels accepted; bad rows are recorded while good rows still
  land. The request only parses + creates the `ImportJob` row
  (`ImportJobAction`); the worker (`services/import_service.py`) runs via
  BackgroundTasks, owns its own sessions, and commits progress per chunk so
  the poll sees it move.
- MinIO is touched ONLY in `services/minio_import.py` (worker/CLI paths),
  never at request time. Missing MinIO config is reported on the job, not
  fatal. `python -m app.import_images` is the CLI entry.
- Upload caps: media 60MB (sniffed content-type must match), CSV 5MB /
  5000 rows.
- Many domains (orders, serials, content, customers, agents) import `Product`
  / `ProductOut` from this domain's public API — keep `__init__.py` a
  superset.

## Tests

`tests/test_admin_catalog.py`, `tests/test_product_import.py`,
`tests/test_products_pagination.py`, `tests/test_minio_import.py`,
`tests/test_minio_e2e.py`, plus public catalog coverage in
`tests/test_public.py`.
