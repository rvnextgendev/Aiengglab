"""A small, dependency-injected AI architecture reference for learning.

No network, database, or LLM is required. In production, replace the supplied
retriever and generator functions with the existing RAG and provider adapters.
"""
from __future__ import annotations
from dataclasses import dataclass
from time import perf_counter
from typing import Callable
from app.ai_quality.sprint3 import scan_evidence, safe_evidence, evaluate
from app.ai_quality.guardrails import ABSTAIN

@dataclass(frozen=True)
class Request:
    tenant_id: str
    question: str
    provider: str = "ollama"
    use_llm: bool = True

def run(request: Request, retrieve: Callable, generate: Callable,
        observe: Callable | None = None) -> dict:
    """Orchestrate: validate -> retrieve -> guard -> generate -> evaluate -> observe."""
    started = perf_counter()
    if not request.tenant_id or not 1 <= len(request.question.strip()) <= 500:
        raise ValueError("Tenant and a valid question are required")
    if request.provider not in {"ollama", "openai-compatible"}:
        raise ValueError("Unsupported provider")
    status = "failed"
    try:
        hits = retrieve(request.tenant_id, request.question)
        if not isinstance(hits, list):
            raise ValueError("Retriever must return a list")
        scan = scan_evidence(hits)
        clean = safe_evidence(hits)
        if not hits:
            result = {"answer": ABSTAIN, "status": "no_evidence", "sources": []}
        elif not scan["safe"]:
            result = {"answer": ABSTAIN, "status": "blocked", "sources": []}
        elif not request.use_llm:
            result = {"answer": "Relevant evidence: " + " | ".join(
                f"[{h['source']}] {h['text']}" for h in clean),
                "status": "evidence_only", "sources": clean}
        else:
            raw = generate(request.question, clean, request.provider)
            checked = evaluate(raw, clean)
            result = {"answer": checked["answer"],
                      "status": "accepted" if checked["passed"] else "abstained",
                      "sources": clean}
        status = result["status"]
        return result
    finally:
        if observe is not None:
            observe(tenant_id=request.tenant_id, operation="architecture_demo",
                    provider=request.provider, latency_ms=(perf_counter()-started)*1000,
                    status=status)
