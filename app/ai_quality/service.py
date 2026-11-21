"""Quality-gated answer endpoint using existing tenant-scoped hybrid search."""
import time
from app.ai_workflows.providers import generate
from app.advanced_rag.retrieval import hybrid_search
from app.ai_quality.guardrails import validate_question, evidence_budget, apply_answer_policy
from app.ai_quality.observability import measure

def quality_answer(tenant_id: str, question: str, provider: str = "ollama",
                   model: str | None = None, limit: int = 3,
                   rerank: bool = False, use_llm: bool = True) -> dict:
    started = time.perf_counter()
    question = validate_question(question)
    if provider not in {"ollama", "openai-compatible"}:
        raise ValueError("Unsupported provider")
    if not 1 <= limit <= 10:
        raise ValueError("Invalid limit")
    with measure("quality_retrieval"):
        hits = evidence_budget(hybrid_search(tenant_id, question, limit, rerank))
    if not hits:
        result = apply_answer_policy("", [])
    elif use_llm:
        with measure("quality_generation", provider=provider):
            answer = generate(question, hits, provider, model)
        result = apply_answer_policy(answer, hits)
    else:
        answer = "Relevant evidence: " + " | ".join(
            f"[{hit['source']}] {hit['text']}" for hit in hits)
        result = apply_answer_policy(answer, hits)
    return {"question": question, **result, "sources": hits,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
