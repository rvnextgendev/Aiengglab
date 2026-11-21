"""Quality service tests without live models or PostgreSQL."""
from app.ai_quality import service
from app.ai_quality.guardrails import ABSTAIN

def test_retrieval_only_has_valid_citations(monkeypatch):
    monkeypatch.setattr(service, "hybrid_search", lambda *args: [
        {"source": "policy.pdf:page-2:chunk-0", "text": "Return within 14 days"}])
    result = service.quality_answer("tenant-a", "Return policy?", use_llm=False)
    assert result["quality_status"] == "citation_check_passed"
    assert result["citation_check"]["valid"]

def test_uncited_model_output_is_blocked(monkeypatch):
    monkeypatch.setattr(service, "hybrid_search", lambda *args: [
        {"source": "policy.pdf:page-2:chunk-0", "text": "Return within 14 days"}])
    monkeypatch.setattr(service, "generate", lambda *args: "Returns within 14 days")
    result = service.quality_answer("tenant-a", "Return policy?")
    assert result["answer"] == ABSTAIN
    assert result["quality_status"] == "citation_check_failed"

def test_no_evidence_abstains(monkeypatch):
    monkeypatch.setattr(service, "hybrid_search", lambda *args: [])
    monkeypatch.setattr(service, "generate", lambda *args: (_ for _ in ()).throw(AssertionError("LLM called")))
    assert service.quality_answer("tenant-a", "Unknown?")["quality_status"] == "no_evidence"
