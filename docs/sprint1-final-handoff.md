# Sprint 1 final implementation handoff

## Changes committed
- Atomic Redis upload reservations prevent duplicate queue admission for identical tenant + filename + content. An orphan-recovery helper can compare-and-delete a reservation when its RQ job is absent.
- A SQLite writer lock serializes approval and cancellation operations on a single shared filesystem. This is intentionally a local pilot mechanism; it is NOT a distributed lock.
- Durable workflow creation now reserves a thread ID in the idempotency claim before invoking LangGraph. A repeated request can inspect its saved checkpoint and recover the result after a crash without executing the graph again.
- Repeated approvals can return a completed checkpoint instead of running the LLM again.
- Cancellation returns conflict for already completed workflows and reports cancelled for unfinished workflows.
- Existing RQ failure registry, Redis replay reservation, shared circuit breaker, cooperative deadlines, and offline failure-injection tests remain available.
- GitHub Actions workflow for syntax and offline tests is added.

## Try it
```powershell
git fetch origin
git switch feature/phase5-production-hardening
pip install -r requirements-phase4.txt
python -m examples.sprint1_all_features_print
pytest -q tests/test_reliability.py tests/test_sprint1_failure_injection.py tests/test_sprint1_reconciliation.py tests/test_sprint1_final_controls.py tests/test_durable_workflows.py
```

## Known limitations and release gates
**Do not call this production-ready.** Tests have not been run successfully by this assistant; no GitHub Actions run was visible for the latest commit.

1. Automatic workflow recovery is limited to safe reconciliation of repeated idempotent requests and checkpoint inspection; it does not autonomously restart failed external side effects. A background sweeper/worker and operation audit trail are still needed.
2. SQLite workflow lock and SQLite checkpointer require a single host/shared filesystem. Move to PostgreSQL checkpointer and transactional locking before multi-instance deployment.
3. Redis upload reservations may outlive a failed enqueue; use `reconcile_upload` after an appropriate grace period. Do not automatically delete a just-created reservation before enqueue finishes.
4. RQ ingestion can still race at the database level when different document bytes share tenant+filename. Add PostgreSQL row/advisory locks to serialize replacements.
5. Failed-job replay reservations prevent concurrent replay but do not yet provide audit logs or robust recovery after enqueue uncertainty.
6. Shared Redis breaker requires real multi-worker tests and stronger probe lease expiration handling.
7. Cooperative deadlines cannot forcibly interrupt a synchronous blocking call.
8. Approval policies are not universally enforced on older answer endpoints.
9. Full CI, real Redis/PostgreSQL/Ollama integration tests, load tests, backup/restore and staged rollout remain mandatory.

## Simple mental model
Retry = try again. Circuit breaker = stop calling a broken provider. Idempotency = same receipt, same operation. Cancellation = stop at the next safe point. Deadline = stop when time budget runs out. Recovery = check saved progress before deciding to rerun. DLQ = keep exhausted jobs for inspection. Replay lock = only one admin can resubmit the same failed job.
