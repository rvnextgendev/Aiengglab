# AriNova AI Architect — integrated learning POC

## Goal
Understand a single end-to-end AI system: upload -> indexing -> retrieval -> LangGraph human approval -> model -> answer evaluation -> feedback -> usage monitoring.

This implementation reuses existing APIs and storage. It does **not** claim to be production-ready or to have been executed against a live database.

## 1. File map
| File | Responsibility |
|---|---|
| `app/rag_api.py` | Authenticated upload, job status, workflow start/status/approval, feedback and usage endpoints |
| `app/advanced_rag/jobs.py` | Enqueue upload using Redis/RQ |
| `app/advanced_rag/ingestion.py` | Extract PDF/TXT pages, chunk, embed and persist |
| `app/advanced_rag/retrieval.py` | Tenant-scoped hybrid keyword + vector search |
| `app/ai_workflows/durable.py` | LangGraph state, edges, human interrupt, checkpoint/resume |
| `app/ai_workflows/integrated.py` | New answer evaluation node and redacted approval preview |
| `app/ai_workflows/providers.py` | Switch between Ollama and OpenAI-compatible models |
| `app/ai_quality/guardrails.py` | Validate citation source IDs |
| `app/ai_quality/sprint3.py` | Basic injection patterns and PII masking |
| `app/ai_workflows/feedback.py` | New tenant-scoped user ratings and comments in SQLite |
| `app/observability/sprint4.py` | Optional latency and estimated token metrics |
| `examples/integrated_architect_print_demo.py` | Learning walkthrough without external services |
| `tests/test_integrated_architect.py` | Feedback isolation, PII masking and node tests |

## 2. Understand the important code, line by line

### A. Upload
```python
job_id = enqueue_document(principal.tenant_id, name, data)
```
- `principal.tenant_id`: tenant comes from authenticated JWT, not a user-supplied tenant parameter.
- `name`: uploaded filename.
- `data`: bytes from the PDF/TXT.
- `enqueue_document`: puts work into Redis RQ and returns a job ID.
- RQ worker runs `ingest_file` to extract, chunk, embed and store the document.
- Upload returns before indexing is finished; poll `GET /rag/jobs/{job_id}`.

### B. LangGraph workflow
```python
builder.add_edge(START, "validate")
builder.add_edge("validate", "retrieve")
builder.add_conditional_edges("retrieve", route_after_retrieve, ...)
builder.add_conditional_edges("approval", route_after_approval, ...)
```
- `START`: begin the graph.
- `validate`: check user question.
- `retrieve`: search tenant-specific chunks.
- `route_after_retrieve`: if no evidence, abstain; if LLM is disabled, skip approval; otherwise ask reviewer.
- `approval`: calls `interrupt()` and stores checkpoint.
- `Command(resume={"approved": True, ...})`: resumes the same thread after reviewer decision.

### C. New integrated answer node
```python
hits = evidence_budget(state.get("sources", []))
scan = scan_evidence(hits)
clean = safe_evidence(hits)
answer = generate(state["question"], clean, provider, state.get("model"))
verdict = apply_answer_policy(answer, clean)
```
- `hits`: retrieved evidence, limited to a safe size.
- `scan`: flag some suspicious instructions in document text.
- `clean`: mask common emails/phone numbers before model input.
- `generate`: call the selected LLM provider.
- `apply_answer_policy`: accept only if bracketed source IDs refer to retrieved evidence.
- If citations fail, return an abstention message.
- `record(...)`: optionally write tenant-scoped metrics.

Important: citation-ID validation is **not** semantic truth checking. Regex-based scanning is only a basic teaching guardrail.

### D. New feedback store
```python
feedback.submit(thread_id, tenant_id, user_id, rating, comment)
```
- `thread_id`: unique LangGraph workflow ID.
- `tenant_id`: keep tenants isolated.
- `user_id`: who submitted feedback.
- `rating`: integer 1–5.
- `comment`: optional short explanation.
- SQLite `PRIMARY KEY(thread_id, tenant_id, user_id)`: one current rating per user/workflow; repeat submissions update it.

### E. Usage monitoring
```python
record(tenant_id, "durable_answer", provider, latency_ms, success,
       input_chars, output_chars)
```
- Records timing, success and approximate token counts.
- Characters / 4 is only an estimate; this is not actual provider billing.

## 3. Live API journey

**Prerequisites:** FastAPI running, valid JWT, Redis server and RQ worker running, PostgreSQL with document tables and embeddings, Ollama or configured compatible model. Use the existing application setup for those services.

1. `POST /rag/upload` multipart file upload, admin/editor JWT. Returns `job_id`.
2. `GET /rag/jobs/{job_id}` until status is `finished`.
3. `POST /rag/workflows` with:
```json
{"question":"What is the return period?","provider":"ollama","use_llm":true,"limit":3,"rerank":false}
```
   The response contains `thread_id` and usually `waiting_approval` when evidence was found.
4. `GET /rag/approval-queue` as admin/editor when PostgreSQL approval store is enabled.
5. `POST /rag/workflows/{thread_id}/approval` as admin/editor:
```json
{"approved":true,"reason":"Evidence looks relevant"}
```
6. `GET /rag/workflows/{thread_id}` to read answer, quality_status and citation_check.
7. `POST /rag/workflows/{thread_id}/feedback` as workflow owner or admin:
```json
{"rating":5,"comment":"Helpful explanation"}
```
8. `GET /rag/workflows/{thread_id}/feedback` as admin/editor.
9. `GET /rag/usage-summary` as admin (enable `AI_USAGE_METRICS=on`).

Note: If retrieval returns no evidence, the graph abstains without approval. If `use_llm=false`, approval is bypassed and evidence-only output is generated.

## 4. Run the learning demo
```powershell
git fetch origin
git switch feature/phase5-production-hardening
pip install -r requirements-phase5-sprint2.txt
python -m examples.integrated_architect_print_demo
pytest -q tests/test_integrated_architect.py
```

The print demo **illustrates** upload and approval; it does not actually enqueue an upload or call LangGraph/Ollama. The real API endpoints above execute those components.

## 5. POC architecture decisions and known limitations
- Reuse the existing ingestion and LangGraph modules rather than implementing a parallel fake service.
- Feedback and metrics use local SQLite; checkpointing can use SQLite or PostgreSQL. This is fine for learning but not fully distributed.
- The workflow state includes retrieved evidence. The status response and approval preview mask common PII, but full sensitive-data governance is not implemented.
- Human approval gates LLM generation only when `use_llm=true` and retrieval finds evidence.
- Evaluation checks source IDs, not claim-level groundedness.
- The quality-answer endpoint and durable workflow are separate paths; the new integrated quality node is wired into the **durable workflow** path.
- No single frontend page is added in this increment. The full workflow is accessible through the existing FastAPI endpoints.
- Tests are committed but not run by the connector. No merge to main.

## 6. Next architect-level lessons
Add a small UI page, a semantic answer judge, prompt versioning, model routing policy, and a feedback-to-evaluation dataset loop. These improve architectural understanding more than adding unrelated agents.
