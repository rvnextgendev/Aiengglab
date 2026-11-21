"""Mocked end-to-end hybrid RAG answer tests."""
import pytest
from app.advanced_rag import answer

def test_answer_uses_hybrid_sources(monkeypatch):
    calls = []
    monkeypatch.setattr(answer, "hybrid_search", lambda tenant, q, limit, rerank: [
        {"id": 1, "text": "Return within 14 days", "source": "policy.pdf:page-2:chunk-0", "score": 0.02}])
    monkeypatch.setattr(answer, "ollama_answer", lambda q, hits: calls.append(hits) or "14 days")
    result = answer.hybrid_answer("tenant-a", "Return policy?")
    assert result["answer"] == "14 days"
    assert calls[0][0]["source"] == "policy.pdf:page-2:chunk-0"

def test_no_evidence_does_not_call_llm(monkeypatch):
    monkeypatch.setattr(answer, "hybrid_search", lambda *args: [])
    monkeypatch.setattr(answer, "ollama_answer", lambda *args: pytest.fail("LLM called"))
    assert answer.hybrid_answer("tenant-a", "Unknown?")["answer"] == answer.ABSTAIN
