"""Offline tests for LangGraph routing, provider selection and tool safety."""
import pytest
from app.ai_workflows import graph, tools, providers

def test_graph_answer_without_llm(monkeypatch):
    monkeypatch.setattr(tools, "hybrid_search", lambda tenant, question, limit, rerank: [
        {"source": "policy.pdf:page-2", "text": "14 day returns", "score": 0.03}])
    result = graph.run_workflow("tenant-a", "viewer", "Return policy?", use_llm=False)
    assert "14 day returns" in result["answer"]
    assert result["trace"] == ["validated", "retrieved", "answered"]

def test_graph_abstains(monkeypatch):
    monkeypatch.setattr(tools, "hybrid_search", lambda *args: [])
    monkeypatch.setattr(graph, "generate", lambda *args: pytest.fail("LLM must not run"))
    result = graph.run_workflow("tenant-a", "viewer", "Unknown?")
    assert result["answer"] == graph.ABSTAIN
    assert result["trace"][-1] == "abstained"

def test_tool_rejects_unapproved_action():
    with pytest.raises(ValueError):
        tools.execute_tool("run_shell", {"command": "whoami"}, tools.ToolContext("tenant-a", "viewer"))

def test_tool_rejects_tenant_override():
    with pytest.raises(ValueError):
        tools.execute_tool("search_documents", {"question": "test", "tenant_id": "tenant-b"},
                           tools.ToolContext("tenant-a", "viewer"))

def test_invalid_provider():
    with pytest.raises(ValueError):
        graph.run_workflow("tenant-a", "viewer", "test", provider="unknown")

def test_provider_requires_evidence():
    assert providers.generate("Question", []) == graph.ABSTAIN

def test_cloud_provider_requires_configuration(monkeypatch):
    monkeypatch.delenv("OPENAI_COMPATIBLE_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_COMPATIBLE_API_KEY", raising=False)
    with pytest.raises(ValueError):
        providers.generate("Question", [{"source": "doc", "text": "evidence"}],
                           provider="openai-compatible")
