# AriNova AI Engineer Lab

A **runnable Phase 1** of a ten-skill AI engineering learning project. This is a deliberately small, transparent prototype, **not** a production-grade RAG or agent system.

## Quick start (Windows PowerShell)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.api:app --reload
```

In a **second** terminal (activate the same environment):

```powershell
streamlit run app/ui.py
```

Open http://localhost:8501 and ask: `How many paid leave days do employees get?`.
Retrieval-only mode works without a model or API key.

### Optional local LLM

Install Ollama, then run `ollama pull llama3.2:3b` and `ollama serve` (if not already running). Tick **Use local Ollama model** in the UI. Set `OLLAMA_MODEL` and `OLLAMA_URL` environment variables to override defaults.

### Tests

```powershell
pytest -q
```

### Architecture

Streamlit -> FastAPI -> input guardrail -> keyword retrieval -> optional Ollama -> JSON response + `events.jsonl` trace.

### Learning roadmap

| Video topic | Hands-on implementation | Status |
|---|---|---|
| Python basics | Modules, API, tests | Phase 1 |
| LLM fundamentals | Ollama chat | Phase 1 (optional) |
| Context engineering | Grounded system message | Phase 1 (basic) |
| RAG | Keyword retrieval -> embeddings + ChromaDB | Basic only |
| Agents | Document, catalog and calculator tools with LangGraph | Planned |
| Evals & observability | pytest, latency, JSONL -> quality dataset/tracing | Basic only |
| Deployment & LLMOps | Docker, CI, environment config | Planned |
| Guardrails & security | Input validation -> auth, injection tests, isolation | Basic only |
| Fine-tuning | Optional LoRA experiment vs RAG | Planned |
| System design & product | Requirements, tradeoffs, cost, demo | Planned |
| Communication | Stakeholder demo and decision log | Planned |

## Limitations

- Keyword search is **not semantic RAG** and can miss paraphrases.
- The simple prompt-injection regex is only a demonstration, not a security boundary.
- No authentication, user data isolation, file uploads, agent orchestration, or fine-tuning yet.
- `events.jsonl` contains questions and answers; don't use sensitive data in this learning prototype.
- LLM responses can hallucinate; the sources field identifies retrieved passages, not verified sentence-level citations.

## Next milestone

Add PDF/TXT upload, embeddings, ChromaDB, retrieval evaluations, and trustworthy source attribution before implementing agent tools.
