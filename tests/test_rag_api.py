"""API integration tests with dependency mocking; no DB or Ollama required."""
import os
import pytest
pytest.importorskip("sqlalchemy")
pytest.importorskip("pgvector")
from fastapi.testclient import TestClient
from app.lab_api import app
from app import rag_api

client = TestClient(app)

def test_rag_requires_key(monkeypatch):
    monkeypatch.setenv("LAB_API_KEY", "local-test-key")
    response = client.post("/rag/answer", json={"question": "What is the return policy?"})
    assert response.status_code == 401

def test_rag_answer_endpoint(monkeypatch):
    monkeypatch.setenv("LAB_API_KEY", "local-test-key")
    monkeypatch.setattr(rag_api, "answer_question", lambda tenant, question, use_llm, limit, min_score: {
        "question": question, "answer": "14 days", "sources": [{"source": "policy.txt:chunk-0"}],
        "mode": "ollama", "latency_ms": 1.2})
    response = client.post("/rag/answer", headers={"X-API-Key": "local-test-key"},
                           json={"question": "What is the return policy?", "use_llm": True})
    assert response.status_code == 200
    assert response.json()["sources"][0]["source"] == "policy.txt:chunk-0"
