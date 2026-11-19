"""Offline end-to-end orchestration tests with mocked retrieval and LLM."""
import pytest
pytest.importorskip("sqlalchemy")
pytest.importorskip("pgvector")
from app import rag_service

def test_answer_uses_retrieved_evidence(monkeypatch):
    monkeypatch.setattr(rag_service, "search", lambda tenant, question, limit: [
        {"source": "policy.txt:chunk-0", "text": "Unused products: 14-day returns.", "score": 0.91}])
    calls = []
    def fake_llm(question, evidence):
        calls.append((question, evidence))
        return "Unused products can be returned in 14 days [policy.txt:chunk-0]."
    monkeypatch.setattr(rag_service, "ollama_answer", fake_llm)
    result = rag_service.answer_question("arinova-demo", "What is the return policy?")
    assert result["mode"] == "ollama"
    assert result["sources"][0]["source"] == "policy.txt:chunk-0"
    assert calls[0][1][0]["text"] == "Unused products: 14-day returns."

def test_abstain_without_evidence(monkeypatch):
    monkeypatch.setattr(rag_service, "search", lambda *args: [])
    monkeypatch.setattr(rag_service, "ollama_answer", lambda *args: pytest.fail("LLM should not be called"))
    result = rag_service.answer_question("arinova-demo", "Unknown policy?")
    assert result["answer"] == rag_service.ABSTAIN
    assert result["mode"] == "retrieval"

def test_score_threshold(monkeypatch):
    monkeypatch.setattr(rag_service, "search", lambda *args: [
        {"source": "irrelevant", "text": "other", "score": 0.1}])
    result = rag_service.answer_question("arinova-demo", "What is the policy?", use_llm=False)
    assert result["sources"] == []
    assert result["answer"] == rag_service.ABSTAIN

def test_rejects_bad_question(monkeypatch):
    with pytest.raises(ValueError):
        rag_service.answer_question("arinova-demo", "")
