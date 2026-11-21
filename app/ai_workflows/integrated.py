"""POC integration helpers shared by the LangGraph answer node and API.

Existing upload -> Redis/RQ -> PostgreSQL ingestion and durable LangGraph
remain the authoritative workflows. This module adds an evaluation/metrics
boundary without duplicating the document pipeline.
"""
from __future__ import annotations
import os
import time
from app.ai_quality.guardrails import apply_answer_policy, evidence_budget, ABSTAIN
from app.ai_quality.sprint3 import scan_evidence, safe_evidence
from app.ai_workflows.providers import generate

def answer_with_evaluation(state: dict) -> dict:
    """A LangGraph node: scan evidence, generate, validate citations, record metrics."""
    from app.reliability.deadline import check
    started = time.perf_counter()
    check()
    hits = evidence_budget(state.get("sources", []))
    scan = scan_evidence(hits)
    clean = safe_evidence(hits)
    provider = state.get("provider", "ollama")
    use_llm = state.get("use_llm", True)
    if not hits:
        verdict = apply_answer_policy("", [])
    elif not scan["safe"]:
        verdict = apply_answer_policy("", [])
        verdict["quality_status"] = "untrusted_evidence_blocked"
    elif use_llm:
        answer = generate(state["question"], clean, provider, state.get("model"))
        verdict = apply_answer_policy(answer, clean)
    else:
        answer = "Relevant evidence: " + " | ".join(
            f"[{h['source']}] {h['text']}" for h in clean)
        verdict = apply_answer_policy(answer, clean)
    check()
    elapsed = (time.perf_counter() - started) * 1000
    if os.getenv("AI_USAGE_METRICS", "off") == "on":
        from app.observability.sprint4 import record
        record(state["tenant_id"], "durable_answer",
               provider if use_llm else "none", elapsed,
               verdict["quality_status"] == "citation_check_passed",
               len(state["question"]) + sum(len(h["text"]) for h in clean),
               len(verdict["answer"]))
    return {"answer": verdict["answer"], "quality_status": verdict["quality_status"],
            "citation_check": verdict["citation_check"],
            "sources": clean,
            "trace": state.get("trace", []) + ["evaluated"]}

def approval_preview(state: dict) -> list[dict]:
    """Only show redacted excerpts to reviewers."""
    return [{"source": h["source"], "excerpt": h["text"][:300]}
            for h in safe_evidence(evidence_budget(state.get("sources", [])))[:10]]
