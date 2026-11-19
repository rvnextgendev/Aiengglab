"""Authenticated RAG route tests with mocked database/LLM."""
from datetime import datetime, timedelta, timezone
import jwt
import pytest
pytest.importorskip("sqlalchemy")
pytest.importorskip("pgvector")
from fastapi.testclient import TestClient
from app.foundation.settings import Settings, get_settings
from app.lab_api import app
from app import rag_api

SECRET = "local-test-secret-with-at-least-32-characters"
app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, jwt_secret=SECRET, app_env="test")
client = TestClient(app)

def auth(tenant="tenant-a", role="viewer"):
    now = datetime.now(timezone.utc)
    claims = {"sub": "user1", "tenant_id": tenant, "role": role,
              "iss": "arinova-local", "aud": "arinova-api", "iat": now,
              "exp": now + timedelta(minutes=5)}
    return {"Authorization": "Bearer " + jwt.encode(claims, SECRET, algorithm="HS256")}

def test_requires_token():
    assert client.post("/rag/answer", json={"question": "Return policy?"}).status_code == 401

def test_tenant_derived_from_token(monkeypatch):
    seen = []
    def fake_answer(tenant, question, use_llm, limit, min_score):
        seen.append(tenant)
        return {"question": question, "answer": "14 days", "sources": [], "mode": "ollama", "latency_ms": 1}
    monkeypatch.setattr(rag_api, "answer_question", fake_answer)
    for tenant in ("tenant-a", "tenant-b"):
        response = client.post("/rag/answer", headers=auth(tenant),
                               json={"question": "Return policy?", "tenant_id": "spoofed"})
        assert response.status_code == 200
    assert seen == ["tenant-a", "tenant-b"]

def test_viewer_cannot_ingest(monkeypatch):
    monkeypatch.setattr(rag_api, "ingest", lambda *args: pytest.fail("Should not ingest"))
    response = client.post("/rag/ingest", headers=auth(role="viewer"),
                           json={"filename": "policy.txt", "content": "Hello"})
    assert response.status_code == 403

def test_editor_ingests_own_tenant(monkeypatch):
    seen = []
    def fake_ingest(tenant, filename, content):
        seen.append(tenant)
        return {"filename": filename, "chunks": 1}
    monkeypatch.setattr(rag_api, "ingest", fake_ingest)
    response = client.post("/rag/ingest", headers=auth("tenant-b", "editor"),
                           json={"filename": "policy.txt", "content": "Hello"})
    assert response.status_code == 200
    assert seen == ["tenant-b"]

def test_legacy_shared_upload_disabled():
    response = client.post("/lab/documents", headers=auth(role="editor"),
                           json={"filename": "a.txt", "content": "Hello"})
    assert response.status_code == 410
