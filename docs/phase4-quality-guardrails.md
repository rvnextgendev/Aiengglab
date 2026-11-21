# Phase 4 — Quality guardrails, evaluation, and telemetry

Branch: `feature/phase4-evaluation-guardrails`, based on unmerged Phase 3 durable approvals.

## Implemented

- `app/ai_quality/guardrails.py`: question normalization, bounded evidence, safe source IDs, bracketed source reference checking and abstention when references are absent/invalid.
- `app/ai_quality/evaluation.py`: offline precision@k, recall@k and hit-rate@k against expected source IDs.
- `app/ai_quality/observability.py`: latency and operation outcome logging, without prompt or document bodies.
- `app/ai_quality/service.py`: tenant-scoped hybrid retrieval, optional LLM, deterministic citation gate.
- `POST /rag/quality-answer`: authenticated quality-gated answer API.
- `app/lab_ui.py`: basic Phase 4 test interface.
- `tests/test_ai_quality.py` and `tests/test_quality_service.py`: offline deterministic tests.

## Example

```json
{"question":"What is the return policy?","provider":"ollama","use_llm":false,"limit":3,"rerank":false}
```

Call `POST /rag/quality-answer` with a JWT bearer token. Result includes `answer`, `quality_status`, `citation_check`, `sources` and `latency_ms`. With `use_llm=true`, answers without recognized bracketed source IDs are replaced with abstention.

## Run

```powershell
git fetch origin
git switch feature/phase4-evaluation-guardrails
pip install -r requirements-phase4.txt
pytest -q tests/test_ai_quality.py tests/test_quality_service.py
uvicorn app.lab_api:app --reload
```

Full API integration requires migrated PostgreSQL/pgvector and a configured JWT; generation requires Ollama or configured HTTPS compatible API.

## Important limitations

- **Citation reference validation is syntactic, not semantic**. A model can cite an existing document while making an unsupported claim. Groundedness, factual consistency and hallucination checks remain future work.
- The new quality gate is enforced only at `/rag/quality-answer`. Older answer/workflow endpoints can bypass it. For universal enforcement, route all generation through a shared policy service.
- This endpoint does **not** require the Phase 3 human approval. If all model calls require approval, use the checkpointed workflow and enforce the quality policy there before production.
- Metrics evaluate retrieval source IDs, not answer correctness. A real labeled evaluation dataset is required.
- Logging uses the application's configured logger; production OpenTelemetry exporters, dashboards, alerting, cost tracking and PII redaction remain pending.
- No live test run or successful CI status is verified. Do not merge or deploy until verified.
