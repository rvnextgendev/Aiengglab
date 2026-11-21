"""Checkpoint, resume, denial, and tenant/role isolation with temporary SQLite."""
from types import SimpleNamespace
import pytest
from app.ai_workflows import durable, tools, graph

def principal(tenant="a", role="viewer", user="u1"):
    return SimpleNamespace(tenant_id=tenant, role=role, user_id=user)

@pytest.fixture(autouse=True)
def temporary_db(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKFLOW_SQLITE_PATH", str(tmp_path / "workflow.sqlite"))
    monkeypatch.setattr(tools, "hybrid_search", lambda *args: [
        {"source": "policy.pdf:page-2", "text": "Returns in 14 days", "score": 0.03}])

def test_checkpoint_survives_new_connection(monkeypatch):
    monkeypatch.setattr(graph, "generate", lambda *args: "Approved answer")
    p = principal()
    started = durable.start(p, "Return policy?")
    assert started["status"] == "waiting_approval"
    assert durable.status(started["thread_id"], p)["status"] == "waiting_approval"
    result = durable.decide(started["thread_id"], principal(role="editor", user="reviewer"), True)
    assert result["status"] == "completed"
    assert result["answer"] == "Approved answer"
    assert result["reviewer_id"] == "reviewer"

def test_rejection_does_not_call_llm(monkeypatch):
    monkeypatch.setattr(graph, "generate", lambda *args: pytest.fail("LLM must not run"))
    started = durable.start(principal(), "Return policy?")
    result = durable.decide(started["thread_id"], principal(role="admin"), False)
    assert "rejected" in result["answer"].lower()

def test_cross_tenant_access_denied():
    started = durable.start(principal(), "Return policy?")
    with pytest.raises(LookupError):
        durable.status(started["thread_id"], principal("b"))
    with pytest.raises(LookupError):
        durable.decide(started["thread_id"], principal("b", "admin"), True)

def test_viewer_cannot_approve():
    started = durable.start(principal(), "Return policy?")
    with pytest.raises(PermissionError):
        durable.decide(started["thread_id"], principal(role="viewer"), True)

def test_no_approval_for_evidence_only():
    started = durable.start(principal(), "Return policy?", use_llm=False)
    assert started["status"] == "completed"
    assert "14 days" in started["answer"]

def test_cannot_approve_twice(monkeypatch):
    monkeypatch.setattr(graph, "generate", lambda *args: "ok")
    started = durable.start(principal(), "Return policy?")
    durable.decide(started["thread_id"], principal(role="editor"), True)
    with pytest.raises(ValueError):
        durable.decide(started["thread_id"], principal(role="editor"), True)
