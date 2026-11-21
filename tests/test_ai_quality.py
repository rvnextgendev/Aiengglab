"""Deterministic Phase 4 quality checks."""
import pytest
from app.ai_quality.guardrails import (
    validate_question, evidence_budget, verify_source_references, apply_answer_policy, ABSTAIN)
from app.ai_quality.evaluation import retrieval_metrics, evaluate_cases

def test_question_normalization():
    assert validate_question("  return   policy? ") == "return policy?"

def test_question_rejects_long_input():
    with pytest.raises(ValueError):
        validate_question("x" * 501)

def test_evidence_budget():
    hits = [{"source": "policy.pdf:page-2:chunk-0", "text": "abcdef"},
            {"source": "other.pdf:page-1", "text": "xyz"}]
    result = evidence_budget(hits, 7)
    assert sum(len(h["text"]) for h in result) <= 7

def test_citation_validity():
    hits = [{"source": "policy.pdf:page-2", "text": "14 day returns"}]
    assert verify_source_references("14 days [policy.pdf:page-2]", hits)["valid"]
    assert not verify_source_references("14 days [fake.pdf:page-1]", hits)["valid"]

def test_answer_abstains_when_uncited():
    hits = [{"source": "policy.pdf:page-2", "text": "14 day returns"}]
    result = apply_answer_policy("14 days", hits)
    assert result["answer"] == ABSTAIN
    assert result["quality_status"] == "citation_check_failed"

def test_retrieval_metrics():
    result = retrieval_metrics(["doc-a", "doc-b"], ["doc-a", "doc-c", "doc-b"], 3)
    assert result["recall_at_k"] == 1.0
    assert result["hit_at_k"]

def test_evaluate_cases():
    result = evaluate_cases([{"question": "returns?", "expected_sources": ["policy.pdf:page-2"]}],
                            lambda q, k: [{"source": "policy.pdf:page-2"}])
    assert result["hit_rate_at_k"] == 1.0
