"""Offline retrieval and citation quality metrics."""
from dataclasses import dataclass
from statistics import mean
from app.ai_quality.guardrails import verify_source_references

@dataclass(frozen=True)
class EvaluationCase:
    question: str
    expected_sources: tuple[str, ...]

def retrieval_metrics(expected_sources: list[str], returned_sources: list[str], k: int = 3) -> dict:
    if not 1 <= k <= 100:
        raise ValueError("Invalid k")
    expected = set(expected_sources)
    returned = returned_sources[:k]
    matches = len(expected.intersection(returned))
    return {"precision_at_k": round(matches / k, 4),
            "recall_at_k": round(matches / len(expected), 4) if expected else 0.0,
            "hit_at_k": bool(matches)}

def evaluate_cases(cases: list[dict], search_fn, k: int = 3) -> dict:
    """search_fn(question, k) -> list of hits with source field."""
    if not cases:
        raise ValueError("At least one evaluation case required")
    rows = []
    for case in cases:
        hits = search_fn(case["question"], k)
        scores = retrieval_metrics(case["expected_sources"],
                                   [h["source"] for h in hits], k)
        rows.append({"question": case["question"], **scores})
    return {"cases": len(rows),
            "mean_precision_at_k": round(mean(r["precision_at_k"] for r in rows), 4),
            "mean_recall_at_k": round(mean(r["recall_at_k"] for r in rows), 4),
            "hit_rate_at_k": round(mean(float(r["hit_at_k"]) for r in rows), 4),
            "details": rows}
