# Persistent RAG with PostgreSQL + pgvector

This optional feature lives alongside the existing keyword/semantic learning lab.

## Flow

TXT document -> normalize/split -> sentence-transformers embeddings (384 dimensions) -> PostgreSQL rag_documents/rag_chunks -> cosine similarity search -> evidence with chunk citations.

## Local Windows setup

1. Install Docker Desktop and ensure it is running.
2. Copy .env.example to .env and replace both passwords/keys with strong local secrets. Avoid committing .env.
3. Run `docker compose -f compose.rag.yaml up -d db`.
4. Create a Python 3.11 virtual environment and install `pip install -r requirements-rag.txt`.
5. Set DATABASE_URL for your Windows host (localhost:5432, not db:5432). Example:
   `$env:DATABASE_URL="postgresql+psycopg://arinova:YOUR_PASSWORD@localhost:5432/arinova"`
6. Set `$env:LAB_API_KEY="YOUR_KEY"`.
7. Run `uvicorn app.lab_api:app --reload`.
8. Open http://localhost:8000/docs, authorize with X-API-Key on /rag endpoints, and call POST /rag/initialize.
9. Call POST /rag/ingest with `{"filename":"policy.txt","content":"Unused products can be returned within 14 days."}`.
10. Call POST /rag/search with `{"question":"How long can I return unused products?","limit":3}`.

The first embedding run downloads the all-MiniLM-L6-v2 model; subsequent runs use the local cache.

## Important notes

- This is a single-tenant local demo. RAG_TENANT_ID is server-controlled; no client-supplied tenant authorization.
- Persistent search returns evidence, not generated LLM prose. The existing /lab/ask endpoint remains unchanged.
- The database persists through a Docker volume. Documents with the same filename are replaced on re-ingest.
- The 384-dimensional vector column is tied to the configured embedding model. Changing models requires migration and re-embedding.
- Similarity alone does not guarantee relevance; evaluate retrieval thresholds and quality before production.
- No PDF ingestion, multi-user authentication, background ingestion, or database migration framework yet.
- The /rag/initialize endpoint is for local learning only. Restrict schema management to deployment migrations in production.
- Never upload confidential data or expose this demo publicly.

## Ollama-grounded answers and Streamlit

- Pull a local model: `ollama pull llama3.2:3b`; ensure Ollama is running.
- Call POST /rag/answer with `{"question":"How long can I return unused products?","use_llm":true,"limit":3,"min_score":0.35}` and X-API-Key.
- The server retrieves pgvector chunks, filters by cosine similarity, and passes evidence to the existing Ollama prompt. It returns answer, source chunks, mode, and latency.
- If no chunks meet the threshold, the API abstains without calling Ollama.
- Run `streamlit run app/lab_ui.py` and use the Persistent RAG section in the Documents + RAG tab.
- Run offline unit/API tests: `pytest -q tests/test_persistent_rag.py tests/test_rag_service.py tests/test_rag_api.py`.
- Database + Ollama end-to-end verification must be performed locally; these automated tests mock external services.
- The default threshold 0.35 is only a starting point, not a calibrated relevance guarantee.
- This is not sentence-level verified citation: the model is instructed to cite sources, but citations are not independently validated.
