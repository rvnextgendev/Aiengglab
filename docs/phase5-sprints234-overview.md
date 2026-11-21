# AriNova Phase 5 — Sprints 2, 3 and 4 prototype

## Sprint 2: remember workflow progress
- `app/ai_workflows/durable.py`: LangGraph nodes, checkpointed workflow, pause with `interrupt()`, resume with `Command(resume=...)`.
- `app/ai_workflows/postgres_store.py`: optional PostgreSQL checkpoint persistence.
- `app/ai_workflows/approval_store.py`: pending approvals, expiry, decisions, audit history.
- `app/rag_api.py`: review queue and history endpoints.

## Sprint 3: safer answers
- `app/ai_quality/sprint3.py`: simple prompt-injection pattern scan, email/phone redaction, citation checks.
- `app/ai_quality/evaluation.py`: offline labeled evaluation helper.
- `app/ai_quality/service.py`: blocks flagged evidence and redacts evidence before sending to the LLM.

**Caveat:** Pattern detection is not robust prompt-injection protection, PII detection is incomplete, and citation validity is NOT semantic factual accuracy.

## Sprint 4: measure usage and cost
- `app/observability/sprint4.py`: optional tenant-scoped local SQLite request metrics.
- `app/observability/costs.py`: configurable rough cost estimates and threshold alerts.
- Metrics are enabled for quality-answer requests with `AI_USAGE_METRICS=on`.
- Estimated tokens use characters / 4; this is NOT actual provider token accounting.

## Run offline demos
```powershell
pip install -r requirements-phase5-sprint2.txt
python -m examples.sprint2_print_demo
python -m examples.sprints234_print_demo
pytest -q tests/test_sprint2_graph.py tests/test_sprints234.py tests/test_sprint4_costs.py
```

## Prototype limits
- No tests executed by the GitHub connector; GitHub commit success is not runtime validation.
- Shared PostgreSQL checkpoints do not make SQLite cancellation and workflow locks distributed.
- Approval event persistence happens after graph resume; it is not an atomic cross-store transaction.
- Pattern-based injection scanning and regex PII redaction are only introductory guards.
- Sprint 4 does not yet provide OpenTelemetry distributed traces, Prometheus dashboards, actual billed token counts, alert delivery, or retention policies.
- No changes merged to main.
