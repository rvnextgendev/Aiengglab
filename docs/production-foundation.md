# Phase 1: Production foundation (feature branch)

This is a foundation for production hardening, **not a production deployment approval**.

## What changed

- `app/foundation/settings.py`: Pydantic Settings reads environment variables and .env, checks JWT secret length and production database URL.
- `app/foundation/auth.py`: verifies HS256 JWT signature, issuer, audience, expiration and mandatory tenant/role claims; rejects missing or invalid tokens.
- `app/foundation/logging.py`: JSON HTTP logs with correlation IDs. Avoid logging tokens, questions or document content.
- `app/rag_api.py`: derives tenant from verified JWT. Only admin/editor can ingest; viewer may search and answer.
- `app/lab_api.py`: legacy unscoped chat and document upload return HTTP 410 to prevent cross-tenant leakage; stateless price tool remains authenticated; evaluation is admin-only.
- `alembic/`: baseline migration for **new empty databases**. Runtime schema initialization endpoint was removed.
- `tests/`: JWT, authorization and tenant propagation tests.
- `scripts/dev_token.py`: local-only short-lived JWT generator, not a production identity provider.

## Local setup (PowerShell)

```powershell
git switch feature/production-foundation
pip install -r requirements-foundation.txt
Copy-Item .env.example .env
```

Replace JWT_SECRET and POSTGRES_PASSWORD with independent random secrets. Set DATABASE_URL to the local PostgreSQL connection URL, for example `postgresql+psycopg://arinova:<password>@localhost:5432/arinova`. Never commit .env. Use URL encoding for special characters in the password.

```powershell
docker compose -f compose.rag.yaml up -d db
alembic upgrade head
uvicorn app.lab_api:app --reload
```

In another terminal, with the same .env:

```powershell
python -m scripts.dev_token --tenant arinova-demo --role editor
```

Copy the token into the Streamlit JWT sidebar field, or send `Authorization: Bearer <token>` in Swagger / HTTP clients. Token expires after 15 minutes.

## Existing database migration warning

The baseline migration creates tables and indexes. If the previous RAG version already created those tables with `create_all()`, **do not run `alembic upgrade head` blindly**. First back up the database, inspect table/index definitions against the migration, reconcile differences (including identity/autoincrement), and only then consider `alembic stamp 0001_initial_rag`. Stamping does not change the schema. Test this procedure on a copy before production use.

## Security limitations and next hardening work

- HS256 local tokens are for development. Production should use an external identity provider, asymmetric JWT validation/JWKS, key rotation and issuer-managed role/tenant claims.
- JWT tenant propagation is implemented in the API and database query predicates. PostgreSQL row-level security and isolation integration tests against a real database are still needed.
- The legacy standalone `app.api` / `app.ui` and direct Python calls are **not protected** by this new API authentication. Do not expose them publicly.
- Alembic baseline needs live migration verification and schema-drift checks.
- No rate limiting, revocation, audit retention policy, secure deployment, or multi-instance log aggregation yet.
- A 401 is expected for protected endpoints without a JWT; /health remains public.
- The old /rag/initialize endpoint is intentionally removed; use Alembic instead.
- The old Streamlit tabs for legacy chat/upload will show HTTP 410. Use the persistent RAG section.
- Do not treat JWT claims from untrusted issuers as verified identity. Protect signing secrets and use HTTPS in deployment.

## Tests

```powershell
pytest -q tests/test_foundation.py tests/test_rag_api.py tests/test_rag_service.py tests/test_persistent_rag.py
```

These tests do not connect to live PostgreSQL or Ollama. Run live integration tests before merging.
