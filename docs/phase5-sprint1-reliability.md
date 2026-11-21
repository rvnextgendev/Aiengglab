# Phase 5 Sprint 1 — Reliability foundation (initial implementation)

Branch `feature/phase5-production-hardening`, based on Phase 4.

## Implemented

- `app/reliability/resilience.py`: bounded exponential backoff with randomized jitter, deadline checks, thread-safe per-process circuit breaker (closed/open/half-open recovery probe).
- `app/ai_workflows/providers.py`: routes transient HTTP/transport failures through the resilience policy. Non-transient 4xx and invalid responses are not retried. Provider requests have HTTPX timeouts.
- `app/reliability/idempotency.py`: SQLite atomic idempotency claims for the persistent-workflow start endpoint; scoped to tenant, user, operation and request key. Reuse with the same request returns the previous result; reuse with changed content is a conflict.
- `app/rag_api.py`: accepts optional `Idempotency-Key` header on `POST /rag/workflows`.
- `app/advanced_rag/jobs.py`: RQ background ingestion retry policy (3 retries after initial attempt, delays 10, 30, 90 seconds), failure status. RQ's `FailedJobRegistry` is the initial failed-job holding area.
- `tests/test_reliability.py`: deterministic tests for transient retry, permanent failures, circuit opening and idempotency.

## Run

```powershell
git fetch origin
git switch feature/phase5-production-hardening
pip install -r requirements-phase4.txt
pytest -q tests/test_reliability.py tests/test_ai_quality.py tests/test_durable_workflows.py
```

Start your Redis workers using your existing Phase 2 worker command. RQ scheduled retry intervals require a worker configured to process scheduled jobs (e.g. `rq worker --with-scheduler arinova-ingestion`).

## Example

```http
POST /rag/workflows
Authorization: Bearer <jwt>
Idempotency-Key: create-arinova-request-0001
Content-Type: application/json

{"question":"What is the return policy?","provider":"ollama","use_llm":true}
```

The same actor, tenant, key and identical body returns the saved result after completion. Different body with same key returns HTTP 409.

## Still required before claiming Sprint 1 or production complete

- **Recovery and cancellation**: the earlier Phase 3 status/resume functionality exists, but cancellation, approval expiration, recovery reconciliation and explicit retry of failed workflows are NOT implemented.
- **Dead-letter replay**: failed RQ jobs are retained in RQ's failed-job registry; no separate dead-letter queue, tenant-safe administrative listing or controlled replay endpoint exists.
- **Idempotency crash recovery**: a crash after claim but before result commit leaves `pending` until manually reconciled. The local SQLite claim store is NOT multi-instance safe when deployed on separate hosts. Approval and ingestion endpoints are not yet idempotency protected.
- **Timeouts**: HTTPX call timeouts and retry deadline are bounded, but the synchronous request cannot forcibly cancel an in-flight blocking call; no end-to-end cancellation propagation.
- **Circuit breakers**: state is in-memory per Python process, not shared across workers. A production multi-instance deployment needs shared state or gateway-level circuit breaking.
- **Retries**: ingestion retries can repeat side effects unless ingestion writes are made idempotent. Check duplicate behavior before enabling in production.
- **Validation**: no local execution or CI success has been verified. Run the tests, integration tests with Redis/Postgres/Ollama, and failure-injection tests.
- **All Phase 5 remaining sprints**: durable PostgreSQL checkpoints, concurrency locking, universal approval/quality policies, security and tenant tests, OpenTelemetry, quotas, staging, CI/CD and load testing.

This branch is an **incremental implementation**, not a production-ready release.
