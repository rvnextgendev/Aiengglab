"""LangGraph: validate -> retrieve -> (answer | abstain) -> finish."""
from __future__ import annotations
from app.reliability.deadline import check
import time
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from app.core import safe_question
from app.ai_workflows.providers import generate
from app.ai_workflows.tools import ToolContext, execute_tool

ABSTAIN = "I do not know based on the documents."

class WorkflowState(TypedDict, total=False):
    question: str
    tenant_id: str
    role: str
    provider: str
    model: str | None
    rerank: bool
    use_llm: bool
    limit: int
    sources: list[dict]
    answer: str
    trace: list[str]

def validate(state: WorkflowState) -> dict:
    check()
    return {"question": safe_question(state["question"]), "trace": ["validated"]}

def retrieve(state: WorkflowState) -> dict:
    check()
    result = execute_tool(
        "search_documents",
        {"question": state["question"], "limit": state.get("limit", 3),
         "rerank": state.get("rerank", False)},
        ToolContext(state["tenant_id"], state["role"]))
    check()
    return {"sources": result["sources"], "trace": state["trace"] + ["retrieved"]}

def route(state: WorkflowState) -> str:
    return "answer" if state["sources"] else "abstain"

def answer(state: WorkflowState) -> dict:
    check()
    hits = state["sources"]
    if state.get("use_llm", True):
        response = generate(state["question"], hits,
                            state.get("provider", "ollama"), state.get("model"))
    else:
        response = "Relevant evidence: " + " | ".join(
            f"[{h['source']}] {h['text']}" for h in hits)
    check()
    return {"answer": response, "trace": state["trace"] + ["answered"]}

def abstain(state: WorkflowState) -> dict:
    return {"answer": ABSTAIN, "trace": state["trace"] + ["abstained"]}

def build_graph():
    builder = StateGraph(WorkflowState)
    builder.add_node("validate", validate)
    builder.add_node("retrieve", retrieve)
    builder.add_node("answer", answer)
    builder.add_node("abstain", abstain)
    builder.add_edge(START, "validate")
    builder.add_edge("validate", "retrieve")
    builder.add_conditional_edges("retrieve", route,
                                  {"answer": "answer", "abstain": "abstain"})
    builder.add_edge("answer", END)
    builder.add_edge("abstain", END)
    return builder.compile()

def run_workflow(tenant_id: str, role: str, question: str,
                 provider: str = "ollama", model: str | None = None,
                 use_llm: bool = True, rerank: bool = False, limit: int = 3) -> dict:
    started = time.perf_counter()
    if provider not in {"ollama", "openai-compatible"}:
        raise ValueError("Unsupported provider")
    if model is not None and (len(model) > 120 or not model.strip()):
        raise ValueError("Invalid model")
    state = build_graph().invoke({
        "tenant_id": tenant_id, "role": role, "question": question,
        "provider": provider, "model": model, "use_llm": use_llm,
        "rerank": rerank, "limit": limit})
    return {"question": state["question"], "answer": state["answer"],
            "sources": state.get("sources", []), "trace": state["trace"],
            "provider": provider if use_llm and state.get("sources") else "none",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
