# Sprint 1 continuation — implementation and limits

## Added
- Cancellation-intent storage scoped to tenant and workflow owner; admin may cancel within tenant.
- Cooperative checks in LangGraph validate/retrieve/answer nodes, including checks after retrieval and generation. Approval is blocked when cancellation was requested.
- Read-only admin recovery inventory; no automatic resumption of pending human approvals or external LLM calls.
- Redis Lua-based shared circuit breaker, opt in with `SHARED_CIRCUIT_BREAKER=true`. Default remains local in-process breaker.
- Cooperative deadline context, applied to durable start/resume, with remaining time passed into HTTPX timeout.
- Tenant-filtered admin failed-job listing and replay through RQ FailedJobRegistry.
- Idempotency keys for workflow start and approval, using local SQLite claims.
- Offline failure-injection tests and a print demo.

## API
- `POST /rag/workflows/{thread_id}/cancel` — owner or tenant admin
- `GET /rag/workflows-recovery` — admin
- `GET /rag/failed-jobs` — admin
- `POST /rag/failed-jobs/{job_id}/replay` — admin
- `Idempotency-Key` optional header for workflow creation and approval.

## Local commands
```powershell
git fetch origin
git switch feature/phase5-production-hardening
pip install -r requirements-phase4.txt
python -m examples.sprint1_remaining_print_demo
pytest -q tests/test_reliability.py tests/test_sprint1_failure_injection.py
```

## Important production gaps

**Not production ready.** This is an incremental implementation with unverified tests.

1. Automatic recovery is **inventory and safe manual intervention only**. It does not automatically replay arbitrary LangGraph nodes. Doing so without durable idempotent side effects can duplicate model calls and writes.
2. Cancellation is cooperative; an already-running HTTP call may finish before the next check. There is no guaranteed kill of a running worker.
3. Idempotency is still local SQLite. Pending claims after crashes need a reconciliation worker; uploads/ingestion are not yet protected by a durable shared dedupe key.
4. RQ failed-job replay creates a new job; concurrent admins may replay the same failed job more than once. No distributed replay lock or replay audit trail yet.
5. Redis shared breaker is opt-in, requires healthy Redis and fails closed on Redis errors; it is not yet load-tested and its probe lease needs distributed lease-expiration hardening.
6. End-to-end deadlines are cooperative, not hard process deadlines. LangGraph synchronous nodes cannot be forcibly interrupted.
7. Cross-worker concurrency locks and shared PostgreSQL checkpointer are deferred to Sprint 2.
8. No live Redis/PostgreSQL/Ollama integration tests or CI execution verified.
9. Some older answer endpoints bypass the durable approval and quality policy.
10. Background job retries can duplicate side effects unless ingestion persistence is made idempotent.

## Next safe step
Run offline tests, fix failures, add live Redis integration tests and transactional shared persistence, then perform fault injection with multiple workers.
