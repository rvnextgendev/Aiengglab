# Phase 2 — Advanced RAG

**Branch:** `feature/phase2-advanced-rag` (based on unmerged Phase 1 `feature/production-foundation`). Do not merge until Phase 1 and Phase 2 tests pass.

## Architecture

Authenticated editor/admin -> POST /rag/upload (PDF/TXT <=5 MB) -> private Redis RQ queue -> worker -> pypdf text extraction -> page-aware chunks -> local embeddings -> PostgreSQL/pgvector. Query -> tenant-scoped pgvector cosine candidates + PostgreSQL full-text candidates -> Reciprocal Rank Fusion -> optional CrossEncoder reranker -> optional Ollama answer with source references.

## Changed files

- `app/advanced_rag/extract.py`: bounded UTF-8 TXT and text-PDF extraction, up to 100 pages and 250,000 characters. Scanned PDFs are not supported (no OCR).
- `app/advanced_rag/ingestion.py`: page-aware chunks and idempotent same-filename/content-hash ingestion.
- `app/advanced_rag/retrieval.py`: pgvector + PostgreSQL full-text search, RRF, optional local reranking.
- `app/advanced_rag/answer.py`: optional Ollama grounded generation.
- `app/advanced_rag/jobs.py`, `worker.py`: Redis RQ background execution and tenant-scoped job status.
- `app/rag_api.py`: authenticated upload, hybrid search, hybrid answer, and job status endpoints.
- `app/lab_ui.py`: Streamlit controls for upload, status, hybrid retrieval.
- `alembic/versions/0002_page_number.py`: optional PDF page number on chunks.
- `compose.rag.yaml`: local Redis service.

## Local setup (PowerShell)

```powershell
git fetch origin
git switch feature/phase2-advanced-rag
pip install -r requirements-phase2.txt
Copy-Item .env.example .env
docker compose -f compose.rag.yaml up -d db redis
alembic upgrade head
```

Configure `DATABASE_URL`, `JWT_SECRET`, and `REDIS_URL` in .env. **Existing databases:** read the Phase 1 migration warning before running Alembic.

Terminal 1:
```powershell
uvicorn app.lab_api:app --reload
```

Terminal 2:
```powershell
python -m app.advanced_rag.worker
```

Terminal 3:
```powershell
streamlit run app/lab_ui.py
```

Generate a local editor token using `python -m scripts.dev_token --tenant arinova-demo --role editor`, then paste into Streamlit sidebar.

## API

- `POST /rag/upload` multipart file; returns `202` and job ID.
- `GET /rag/jobs/{job_id}` checks status for the authenticated tenant.
- `POST /rag/hybrid-search` JSON `{"question":"return policy","limit":3,"rerank":false}`.
- `POST /rag/hybrid-answer` JSON `{"question":"return policy","limit":3,"rerank":true,"use_llm":true}`.

All require bearer JWT; upload requires editor/admin role. Hybrid results include `source` with page and chunk reference. Reranking is optional because it loads an additional local model. A result score is an RRF score or an additional raw reranker score, **not a probability**.

## Safety and readiness gaps

- Redis contains queued raw document bytes, so use private networking, authentication, encryption, retention policies and memory controls before deployment. The local Redis example binds to loopback and is **not production secure**.
- RQ job retries are not configured; failure status is retained temporarily. Add safe retry policies, deduplication across concurrent jobs, dead-letter handling and durable object storage before production.
- Text-based PDFs only. No OCR, malware scanning, PDF sandbox, or trusted document classification.
- RRF retrieves candidates from tenant-filtered SQL, but database row-level security and live cross-tenant tests remain outstanding.
- The optional reranker and embedding models may download weights on first run. Pin exact model revisions before production.
- There is no verified answer-citation checker; Ollama may still hallucinate. Retrieval quality and thresholds need evaluation.
- Existing /rag/answer remains the earlier vector-only endpoint; use /rag/hybrid-answer for Phase 2.
- The initial pgvector HNSW index and migration have not been live-verified; check query plans and schema drift.

## Offline tests

```powershell
pytest -q tests/test_advanced_rag.py tests/test_phase2_answer.py tests/test_foundation.py tests/test_rag_api.py
```

These tests mock the external DB/model path and are not a substitute for a live PostgreSQL/Redis/Ollama integration test.
