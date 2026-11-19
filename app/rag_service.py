"""Grounded answer composition for persistent pgvector retrieval."""
from __future__ import annotations
import time
from app.core import ollama_answer, safe_question
from app.persistent_rag import search

ABSTAIN = "I do not know based on the documents."

def answer_question(tenant_id: str, question: str, use_llm: bool = True,
                    limit: int = 3, min_score: float = 0.35) -> dict:
    start = time.perf_counter()
    question = safe_question(question)
    if not 0 <= min_score <= 1:
        raise ValueError("min_score must be between 0 and 1")
    hits = [hit for hit in search(tenant_id, question, limit)
            if hit["score"] >= min_score]
    if not hits:
        answer = ABSTAIN
    elif use_llm:
        answer = ollama_answer(question, hits)
    else:
        answer = "Relevant evidence: " + " | ".join(
            f"[{hit['source']}] {hit['text']}" for hit in hits)
    return {"question": question, "answer": answer, "sources": hits,
            "mode": "ollama" if use_llm and hits else "retrieval",
            "latency_ms": round((time.perf_counter() - start) * 1000, 2)}
