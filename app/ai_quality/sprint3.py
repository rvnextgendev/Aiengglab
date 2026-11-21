"""Sprint 3: conservative, offline-safe content and citation checks."""
import re
from app.ai_quality.guardrails import ABSTAIN, verify_source_references

INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|system) instructions",
    r"reveal (your |the )?(system prompt|secret|api key)",
    r"you are now (the |a )?(system|developer)",
    r"send (all )?(documents|secrets|credentials) to",
]
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE = re.compile(r"(?<!\d)(?:\+?\d[\d -]{8,}\d)(?!\d)")

def redact_pii(text: str) -> str:
    return PHONE.sub("[PHONE]", EMAIL.sub("[EMAIL]", text))

def scan_evidence(hits: list[dict]) -> dict:
    flagged = []
    for hit in hits:
        body = hit.get("text", "")
        if any(re.search(p, body, re.IGNORECASE) for p in INJECTION_PATTERNS):
            flagged.append(hit.get("source", "unknown"))
    return {"safe": not flagged, "flagged_sources": flagged}

def evaluate(answer: str, hits: list[dict]) -> dict:
    citation = verify_source_references(answer, hits)
    if not hits or not citation["valid"]:
        return {"answer": ABSTAIN, "passed": False, "reason": "missing_or_invalid_citations"}
    return {"answer": answer, "passed": True, "reason": "citation_format_passed"}

def safe_evidence(hits: list[dict]) -> list[dict]:
    return [{**h, "text": redact_pii(h["text"])} for h in hits]
