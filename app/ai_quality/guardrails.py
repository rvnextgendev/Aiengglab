"""Deterministic, conservative guards. Not a substitute for semantic verification."""
import re

ABSTAIN = "I do not know based on the documents."
MAX_QUESTION_CHARS = 500
MAX_EVIDENCE_CHARS = 12000

def validate_question(question: str) -> str:
    if not isinstance(question, str):
        raise ValueError("Question must be text")
    normalized = " ".join(question.split())
    if not normalized or len(normalized) > MAX_QUESTION_CHARS:
        raise ValueError("Question must be 1 to 500 characters")
    return normalized

def evidence_budget(hits: list[dict], max_chars: int = MAX_EVIDENCE_CHARS) -> list[dict]:
    if not 0 < max_chars <= MAX_EVIDENCE_CHARS:
        raise ValueError("Invalid evidence budget")
    output = []
    remaining = max_chars
    for hit in hits[:10]:
        source = hit.get("source")
        content = hit.get("text")
        if not isinstance(source, str) or not isinstance(content, str):
            continue
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", source):
            continue
        if remaining <= 0:
            break
        excerpt = content[:remaining]
        if excerpt.strip():
            output.append({**hit, "text": excerpt})
            remaining -= len(excerpt)
    return output

def verify_source_references(answer: str, hits: list[dict]) -> dict:
    """Check that bracketed source IDs are among retrieved hits.

    This checks reference validity, NOT whether a claim is supported.
    """
    allowed = {h["source"] for h in hits if isinstance(h.get("source"), str)}
    references = re.findall(r"\[([^\[\]\n]{1,200})\]", answer)
    invalid = sorted({ref for ref in references if ref not in allowed})
    valid = sorted({ref for ref in references if ref in allowed})
    return {"valid": bool(valid) and not invalid,
            "cited_sources": valid, "invalid_sources": invalid,
            "has_citations": bool(references)}

def apply_answer_policy(answer: str, hits: list[dict], *, require_citations: bool = True) -> dict:
    if not hits:
        return {"answer": ABSTAIN, "quality_status": "no_evidence",
                "citation_check": verify_source_references("", [])}
    check = verify_source_references(answer, hits)
    if require_citations and not check["valid"]:
        return {"answer": ABSTAIN, "quality_status": "citation_check_failed",
                "citation_check": check}
    return {"answer": answer, "quality_status": "citation_check_passed" if check["valid"] else "unchecked",
            "citation_check": check}
