"""Explicit read-only tool allowlist; never execute model-provided Python or shell."""
from dataclasses import dataclass
from app.advanced_rag.retrieval import hybrid_search

@dataclass(frozen=True)
class ToolContext:
    tenant_id: str
    role: str

def execute_tool(name: str, arguments: dict, context: ToolContext) -> dict:
    if name != "search_documents":
        raise ValueError("Tool is not allowed")
    if context.role not in {"admin", "editor", "viewer"}:
        raise PermissionError("Role not allowed")
    if set(arguments) - {"question", "limit", "rerank"}:
        raise ValueError("Unknown tool arguments")
    question = arguments.get("question")
    limit = arguments.get("limit", 3)
    rerank = arguments.get("rerank", False)
    if not isinstance(question, str) or not 1 <= len(question.strip()) <= 500:
        raise ValueError("Invalid question")
    if type(limit) is not int or not 1 <= limit <= 10 or type(rerank) is not bool:
        raise ValueError("Invalid search options")
    hits = hybrid_search(context.tenant_id, question, limit, rerank)
    return {"sources": hits}
