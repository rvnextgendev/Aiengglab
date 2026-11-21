# Phase 5 Sprint 2 — PostgreSQL checkpoint and human approval prototype

## What changed

1. `app/ai_workflows/postgres_store.py`: opens `PostgresSaver`, initializes LangGraph checkpoint tables, and keeps checkpoints across API restarts.
2. `app/ai_workflows/durable.py`: chooses PostgreSQL when `WORKFLOW_CHECKPOINTER=postgres`; otherwise retains SQLite for simple local development.
3. `app/ai_workflows/approval_store.py`: PostgreSQL tables for pending approvals and approval events, tenant-scoped queue, expiry and audit history.
4. `app/rag_api.py`: adds `GET /rag/approval-queue` (admin/editor) and `GET /rag/workflows/{thread_id}/approval-history` (authorized owner/admin).
5. `examples/sprint2_print_demo.py`: no-database pause/resume demonstration using `MemorySaver` and `print()`.
6. `tests/test_sprint2_graph.py`: offline pause/resume test.

## Simple explanation

- **State** = the workflow's backpack of information (question, sources, answer).
- **Node** = one function that does one job.
- **Edge** = arrow showing which function runs next.
- **Checkpoint** = saved progress.
- **thread_id** = workflow's unique ID used to load its checkpoint.
- **interrupt()** = pause and ask a human.
- **Command(resume=...)** = continue after a human replies.
- **PostgresSaver** = saves checkpoints in PostgreSQL rather than SQLite.

## Setup

```powershell
git fetch origin
git switch feature/phase5-production-hardening
pip install -r requirements-phase5-sprint2.txt
$env:WORKFLOW_CHECKPOINTER="postgres"
$env:WORKFLOW_POSTGRES_URL="postgresql://postgres:password@localhost:5432/arinova"
$env:WORKFLOW_APPROVAL_STORE="postgres"
python -m examples.sprint2_print_demo
pytest -q tests/test_sprint2_graph.py tests/test_durable_workflows.py
```

Use an actual local PostgreSQL URL. The print demo requires no PostgreSQL connection.

## Prototype limitations

- PostgreSQL checkpointing is selectable, but existing cancellation flags and idempotency claims still use SQLite, and the existing workflow lock is SQLite. They are not fully multi-instance safe.
- Approval decisions currently resume the LangGraph workflow before recording the PostgreSQL approval event. If the audit write fails, the two stores may disagree; this needs transactional/outbox design for production.
- The approval request `reason` field is accepted but not yet forwarded into the audit store.
- Expired approvals are excluded from the queue, but expiry is not yet enforced by the LangGraph resume path unless the approval store decision is checked.
- Database schema setup occurs on demand; use migrations for production.
- No live PostgreSQL test run has been verified. Do not claim Sprint 2 is production-ready.
