# Sprint 1 — easy explanation and implementation status

## Simple story
A user asks the AriNova assistant to read a PDF and answer a question.

1. **Retry**: if Ollama is temporarily busy, try again a limited number of times.
2. **Circuit breaker**: if Ollama keeps failing, stop sending new requests temporarily.
3. **Deadline**: do not start more work after the request's time budget expires.
4. **Cancel**: the user requests cancellation; each workflow node checks that flag.
5. **Recovery**: show saved workflows to an administrator; do not automatically replay a possibly completed LLM call.
6. **Idempotency**: the same workflow creation or approval key returns its saved result.
7. **Dead-letter**: failed ingestion jobs are retained by RQ; an admin may replay one.
8. **Replay lock**: a Redis NX key prevents two administrators replaying the same failed job within the reservation window.

## Main code files

- `app/reliability/resilience.py` — retry and in-process circuit breaker.
- `app/reliability/shared_circuit.py` — optional Redis shared circuit breaker.
- `app/reliability/deadline.py` — cooperative time limits.
- `app/reliability/workflow_control.py` — cancellation flags and recovery inventory.
- `app/reliability/idempotency.py` — SQLite idempotency claims.
- `app/reliability/reconcile.py` — list stale claims and flag them for manual reconciliation.
- `app/reliability/dead_letter.py` — failed-job listing and replay.
- `app/reliability/replay_lock.py` — Redis atomic replay reservation.
- `app/advanced_rag/ingestion.py` — existing tenant + filename + SHA256 content-hash check for unchanged files.

## Run
```powershell
git fetch origin
git switch feature/phase5-production-hardening
pip install -r requirements-phase4.txt
python -m examples.sprint1_all_features_print
pytest -q tests/test_reliability.py tests/test_sprint1_failure_injection.py tests/test_sprint1_reconciliation.py
```

## Remaining before Sprint 1 can be signed off
- **Automatic recovery is not implemented**. The inventory and stale-claim detection are read-only by design, because blindly rerunning LLM and ingestion side effects is unsafe. Need durable operation-to-workflow mapping and a reconciliation worker.
- **Upload enqueue idempotency is incomplete**. The ingestion DB layer checks unchanged content hashes but concurrent queue submissions may create multiple jobs; add a Redis atomic dedupe reservation plus cleanup/reconciliation and concurrent database locking.
- **Workflow approval concurrency** is not transactionally serialized across processes. Sprint 2 must add shared PostgreSQL checkpointing and per-thread locking.
- **Idempotency** is local SQLite and pending claims are not automatically reconciled.
- **Replay locking** uses Redis NX, but failure after reserving a replay may require manual repair and replay auditing.
- **Shared circuit breaker** has not been validated against real Redis and needs robust probe lease handling.
- **Cancellation** is cooperative, not forced interruption of a blocking call.
- **Tests** were committed but not executed successfully here; GitHub connector accepts file changes but does not execute CI or Python.
- **Production** requires Redis/PostgreSQL/Ollama integration tests, concurrency fault injection, CI and load testing.

**Status: code added to feature branch; not merged; not production-ready.**
