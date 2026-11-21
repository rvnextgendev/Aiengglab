"""Hybrid retrieval + optional reranking + grounded Ollama response."""
import time
from app.core import ollama_answer, safe_question
from app.advanced_rag.retrieval import hybrid_search
from app.rag_service import ABSTAIN

def hybrid_answer(tenant_id: str, question: str, limit: int = 3,
                  use_reranker: bool = False, use_llm: bool = True) -> dict:
    started = time.perf_counter()
    question = safe_question(question)
    hits = hybrid_search(tenant_id, question, limit, use_reranker)
    if not hits:
        answer = ABSTAIN
    elif use_llm:
        answer = ollama_answer(question, hits)
    else:
        answer = "Relevant evidence: " + " | ".join(
            f"[{hit['source']}] {hit['text']}" for hit in hits)
    return {"question": question, "answer": answer, "sources": hits,
            "mode": "hybrid-rerank" if use_reranker else "hybrid",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
