# Phase 3 — LangGraph AI workflows

**Branch:** `feature/phase3-ai-workflows`, based on unmerged Phase 2. No merge has been performed.

## Architecture

JWT-authenticated request -> `POST /rag/workflow` -> LangGraph validate -> allowlisted tenant-scoped hybrid search -> conditional answer/abstain -> optional Ollama or HTTPS OpenAI-compatible chat completion -> response with sources and execution trace.

## File guide

- `app/ai_workflows/graph.py`: TypedDict workflow state, validate/retrieve/answer/abstain nodes, conditional graph edges, trace and elapsed time.
- `app/ai_workflows/tools.py`: explicit `search_documents` tool allowlist. Tenant is supplied from the verified JWT; arbitrary model-provided code and tenant overrides are rejected.
- `app/ai_workflows/providers.py`: Ollama local chat and optional HTTPS OpenAI-compatible API; bounded timeouts and retries only on transport failures or 429/502/503/504.
- `app/rag_api.py`: authenticated `POST /rag/workflow` endpoint.
- `tests/test_phase3_workflows.py`: offline mocked graph routing, abstention, provider validation and tool authorization tests.
- `requirements-phase3.txt`: LangGraph dependency.

## Local setup (PowerShell)

```powershell
git fetch origin
git switch feature/phase3-ai-workflows
pip install -r requirements-phase3.txt
# Configure .env as described in docs/production-foundation.md
docker compose -f compose.rag.yaml up -d db redis
alembic upgrade head
ollama pull llama3.2:3b
uvicorn app.lab_api:app --reload
```

In another terminal:
```powershell
pytest -q tests/test_phase3_workflows.py
```

Use `python -m scripts.dev_token --tenant arinova-demo --role viewer` in development to create a short-lived JWT.

## Example request

```json
{
  "question": "How many days can I return AriNova shoes?",
  "provider": "ollama",
  "use_llm": true,
  "rerank": false,
  "limit": 3
}
```

`POST /rag/workflow` with `Authorization: Bearer <JWT>`. Set `use_llm: false` for evidence-only mode without an LLM call. To use a cloud provider set `OPENAI_COMPATIBLE_BASE_URL` (HTTPS), `OPENAI_COMPATIBLE_API_KEY`, and `OPENAI_COMPATIBLE_MODEL` in the server environment and set provider to `openai-compatible`. The provider endpoint is server-configured, not supplied by users.

## Limitations and security

- Graph execution is **synchronous per request**, not a durable/resumable workflow. Checkpointing, task persistence and human approval gates are future work.
- No arbitrary agent-driven tool choice: the workflow always calls the single allowlisted read-only search tool. This is deliberate for safety and auditability.
- Provider retries are bounded but not backed by a circuit breaker or request budget; add quotas, concurrency limits and monitoring before public deployment.
- The workflow trace records node names only. No persistent distributed traces or OpenTelemetry yet.
- Prompt instructions alone do not guarantee grounded citations; a citation validator and evaluation suite are still needed.
- External LLM calls transmit retrieved evidence to the configured provider. Add tenant-level data governance, PII redaction and provider allowlists before enabling cloud providers.
- The provider's response may include unsupported statements; do not use it for high-stakes automated decisions.
- Phase 1 and Phase 2 integration tests and migrations remain unverified. Do not merge or deploy until CI and end-to-end checks pass.

## Tests

```powershell
pytest -q tests/test_phase3_workflows.py tests/test_phase2_answer.py tests/test_foundation.py
```
