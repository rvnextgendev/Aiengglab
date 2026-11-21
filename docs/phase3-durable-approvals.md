# Phase 3 extension — persistent checkpoints and human approval

Branch: `feature/phase3-durable-approvals`, based on `feature/phase3-ai-workflows`. No merge into main.

## How it works

1. Authenticated user POSTs to `/rag/workflows`.
2. LangGraph validates and retrieves tenant-filtered evidence.
3. If there are no sources, it abstains. If `use_llm=false`, it returns evidence without human review.
4. Otherwise, `interrupt()` saves the checkpoint to local SQLite and pauses before sending evidence to the LLM.
5. An editor or admin **of the same tenant** calls `POST /rag/workflows/{thread_id}/approval` with `{"approved":true}` or `{"approved":false}`.
6. `Command(resume=...)` continues the saved graph. Approval invokes the configured LLM; rejection ends without an LLM call.
7. `GET /rag/workflows/{thread_id}` returns saved status, sources, trace, and answer to the owner or a tenant admin.

## New files

- `app/ai_workflows/durable.py`: SQLite checkpointer, LangGraph interrupt/resume, identity validation, thread status, approval decisions.
- `tests/test_durable_workflows.py`: offline checkpoint persistence, approval, rejection, tenant isolation, role checks, evidence-only path and duplicate approval.
- `app/lab_ui.py`: start/status/approve/reject controls in Streamlit.
- `app/rag_api.py`: new authenticated workflow endpoints.
- `requirements-phase3.txt`: SQLite checkpointer dependency.

## Local run (PowerShell)

```powershell
git fetch origin
git switch feature/phase3-durable-approvals
pip install -r requirements-phase3.txt
# Configure .env as in docs/production-foundation.md
# Configure WORKFLOW_SQLITE_PATH=.data/workflows.sqlite
uvicorn app.lab_api:app --reload
streamlit run app/lab_ui.py
pytest -q tests/test_durable_workflows.py
```

A PostgreSQL/pgvector database with migrated documents is still required for retrieval. Ollama is required only for approved LLM generation.

## API example

Start (viewer JWT):
```http
POST /rag/workflows
Authorization: Bearer <viewer-token>
Content-Type: application/json

{"question":"What is the return policy?","provider":"ollama","use_llm":true}
```

Expected shape: `{"thread_id":"...","status":"waiting_approval","question":"...","sources":[...],"trace":[...]}`.

Approve (editor/admin JWT in same tenant):
```http
POST /rag/workflows/<thread_id>/approval
Authorization: Bearer <editor-token>
Content-Type: application/json

{"approved":true}
```

Reject with `{"approved":false}`. Check status with `GET /rag/workflows/<thread_id>`.

## Critical production caveats

- This uses **local SQLite** and synchronous request execution. SQLite is appropriate for local learning and single-process development, **not multi-instance production**. For production, use a shared PostgreSQL checkpointer and per-thread concurrency controls.
- Checkpoints store questions, evidence and responses, potentially sensitive tenant data. Protect SQLite file permissions, backups, encryption, retention and deletion. `.data/` is ignored by Git.
- Approval controls are enforced on the new `/rag/workflows` endpoint. Existing `/rag/workflow`, `/rag/hybrid-answer` and `/rag/answer` **still allow generation without human approval**. Disable those endpoints or enforce a common policy before requiring universal approval.
- Approval is checked by role and tenant; the reviewer may be the same user who initiated the workflow. Add separation-of-duties policy if needed.
- Approval does not guarantee idempotent concurrent resumes. Add database-backed per-thread locking and idempotency keys for production.
- There is no expiration policy, cancel operation, audit-event table, email notification, human approval queue listing, or workflow cleanup yet.
- A reviewer approves sending retrieved evidence to the configured provider; the content is visible in the pending state. Review sensitive content before approving a cloud provider.
- The model response is not automatically verified against citations.
- CI, SQLite checkpoint persistence tests and live PostgreSQL/Ollama integration tests **have not been verified as passing**. Do not merge/deploy without executing them.
