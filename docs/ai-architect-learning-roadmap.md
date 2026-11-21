# AriNova AI Architect Learning Roadmap — POC

## Purpose
Learn to design an end-to-end AI application. The goal is architecture understanding, not enterprise deployment.

## End-to-end request
1. **Business requirement**: user asks a question about an uploaded PDF. Define expected answer, evidence and acceptable failure.
2. **UI/API**: Angular or Streamlit sends the question to FastAPI.
3. **Identity**: JWT identifies user, role and tenant. Never trust tenant_id supplied by the client.
4. **Ingestion**: parse PDF/TXT, clean, chunk, embed and store with tenant and source metadata.
5. **Retrieval**: hybrid search combines vector similarity and keyword relevance. Optionally rerank.
6. **Orchestration**: LangGraph connects validate, retrieve, approve, answer and stop nodes.
7. **Human approval**: interrupt() checkpoints workflow; Command(resume=...) continues.
8. **Model gateway**: choose Ollama or OpenAI-compatible provider; apply timeout, retry and breaker.
9. **Guardrails**: scan untrusted evidence, redact common PII, check citation IDs. Citation validity does not prove factual accuracy.
10. **Reliability**: use idempotency keys, cancellation checks, deadlines, background queue, DLQ and replay controls.
11. **Monitoring**: collect provider, latency, status and estimated usage per tenant.
12. **Evaluation**: test representative questions, retrieval precision/recall, groundedness and failure scenarios.
13. **Deployment**: containerize FastAPI, worker, PostgreSQL, Redis and Ollama; keep secrets outside code.
14. **Feedback**: collect reviewer corrections and improve retrieval, prompts, evaluation and model choice.

## Learning example
`app/architecture/reference_pipeline.py` is a deliberately small dependency-injected orchestration:
- `Request`: immutable input object.
- `run(request, retrieve, generate, observe)`: coordinates services without hard-coding providers.
- `retrieve(tenant, question)`: finds evidence only within the tenant.
- `scan_evidence`: flags basic injection patterns.
- `safe_evidence`: masks common PII before the LLM.
- `generate`: injected model function, easy to replace with Ollama.
- `evaluate`: validates citation IDs; does not perform semantic verification.
- `observe`: receives status and latency, even on exceptions.

Run:
```powershell
python -m examples.ai_architect_print_demo
pytest -q tests/test_architecture_reference.py
```

## Code map
| Responsibility | File |
|---|---|
| HTTP endpoints | app/rag_api.py |
| RAG search | app/advanced_rag/retrieval.py |
| Background jobs | app/advanced_rag/jobs.py |
| LangGraph graph | app/ai_workflows/durable.py |
| Provider selection | app/ai_workflows/providers.py |
| Tool authorization | app/ai_workflows/tools.py |
| PostgreSQL checkpoints | app/ai_workflows/postgres_store.py |
| Approval audit | app/ai_workflows/approval_store.py |
| Reliability | app/reliability/ |
| Quality gate | app/ai_quality/service.py |
| Evaluation | app/ai_quality/evaluation.py |
| Metrics | app/observability/sprint4.py |
| Architecture teaching | app/architecture/reference_pipeline.py |

## What's still absent or incomplete (not merely testing)
**For the POC:** A single polished UI journey connecting upload -> indexing -> question -> approval -> answer -> feedback; feedback storage and review; configurable model/prompt selection UI; actual semantic groundedness judge; prompt versioning; a small evaluation dataset with expected factual answers; cost budgets and provider fallback policies.

**For production:** shared distributed workflow locking and cancellation storage; transactional approval checkpoint/audit consistency; robust automatic crash reconciliation; migrations and backup/restore; secrets management; audit and data retention policies; comprehensive authorization review; tracing/metrics export; real token accounting and budget enforcement; scalable workers and capacity planning; CI/CD deployment, staged rollout and incident response.

**Architecture decision tradeoffs:** LangGraph vs plain functions; SQLite vs PostgreSQL; Ollama vs cloud; vector-only vs hybrid search; synchronous API vs queued jobs; deterministic checks vs LLM judge; single tenant vs multi-tenant. Document decisions as short ADRs.

## Suggested learning order
1. Run the dependency-injection reference pipeline.
2. Replace the mock retriever with tenant-scoped hybrid search.
3. Replace the mock generator with the provider adapter.
4. Wrap the pipeline in LangGraph for approval and checkpointing.
5. Add evaluation cases and inspect failures.
6. Add monitoring and rough cost estimates.
7. Connect one UI screen to the complete workflow.

This is a prototype learning artifact, not a guarantee that the integrated application passes live tests.
