"""Persistent LangGraph checkpoints and explicit human approval before LLM generation.

Development storage: local SQLite. For multi-instance production use a shared
PostgreSQL checkpointer and coordinated per-thread locking.
"""
from __future__ import annotations
import os
import re
import time
from pathlib import Path
from uuid import uuid4
from contextlib import contextmanager
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt
from langgraph.checkpoint.sqlite import SqliteSaver
from app.ai_workflows.graph import validate, retrieve, answer, abstain, ABSTAIN
from app.reliability import workflow_control as control
from app.reliability.deadline import deadline, check, OperationCancelled
from app.reliability.locks import workflow_lock

class DurableState(TypedDict, total=False):
    question: str
    tenant_id: str
    user_id: str
    role: str
    provider: str
    model: str | None
    rerank: bool
    use_llm: bool
    limit: int
    sources: list[dict]
    answer: str
    trace: list[str]
    approved: bool
    reviewer_id: str
    thread_id: str

def approval(state: DurableState) -> dict:
    check()
    if control.is_cancelled(state['thread_id']):
        raise OperationCancelled('Workflow cancelled')
    # interrupt() persists the current graph state and returns on resume.
    decision = interrupt({
        "kind": "llm_answer_approval",
        "question": state["question"],
        "sources": [{"source": h["source"], "excerpt": h["text"][:300]}
                    for h in state.get("sources", [])[:10]],
        "message": "Approve sending retrieved evidence to the selected LLM provider?"
    })
    if not isinstance(decision, dict) or type(decision.get("approved")) is not bool:
        raise ValueError("Approval decision must be explicit")
    reviewer = decision.get("reviewer_id", "")
    if not isinstance(reviewer, str) or not reviewer:
        raise ValueError("Reviewer required")
    return {"approved": decision["approved"], "reviewer_id": reviewer,
            "trace": state["trace"] + ["approved" if decision["approved"] else "rejected"]}

def route_after_retrieve(state: DurableState) -> str:
    if not state.get("sources"):
        return "abstain"
    if not state.get("use_llm", True):
        return "answer"
    return "approval"

def route_after_approval(state: DurableState) -> str:
    return "answer" if state["approved"] else "rejected"

def rejected(state: DurableState) -> dict:
    return {"answer": "Human reviewer rejected LLM generation.",
            "trace": state["trace"] + ["stopped"]}

def build_durable_graph(checkpointer):
    builder = StateGraph(DurableState)
    for name, fn in [("validate", validate), ("retrieve", retrieve),
                     ("approval", approval), ("answer", answer),
                     ("abstain", abstain), ("rejected", rejected)]:
        builder.add_node(name, fn)
    builder.add_edge(START, "validate")
    builder.add_edge("validate", "retrieve")
    builder.add_conditional_edges("retrieve", route_after_retrieve,
        {"abstain": "abstain", "answer": "answer", "approval": "approval"})
    builder.add_conditional_edges("approval", route_after_approval,
        {"answer": "answer", "rejected": "rejected"})
    for node in ("answer", "abstain", "rejected"):
        builder.add_edge(node, END)
    return builder.compile(checkpointer=checkpointer)

@contextmanager
def open_graph():
    path = Path(os.environ.get("WORKFLOW_SQLITE_PATH", ".data/workflows.sqlite"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with SqliteSaver.from_conn_string(str(path)) as saver:
        yield build_durable_graph(saver)

def config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}

def view(snapshot) -> dict:
    state = snapshot.values
    waiting = bool(snapshot.next) and "approval" in snapshot.next
    cancelled = control.is_cancelled(snapshot.config["configurable"]["thread_id"])
    return {
        "thread_id": snapshot.config["configurable"]["thread_id"],
        "status": ("cancelled" if cancelled and snapshot.next else
                   "waiting_approval" if waiting else
                   "completed" if not snapshot.next else "running"),
        "question": state.get("question"),
        "answer": state.get("answer"),
        "sources": state.get("sources", []),
        "trace": state.get("trace", []),
        "reviewer_id": state.get("reviewer_id"),
        "cancel_requested": cancelled,
    }

def start(principal, question: str, provider: str = "ollama",
          model: str | None = None, use_llm: bool = True,
          rerank: bool = False, limit: int = 3) -> dict:
    if provider not in {"ollama", "openai-compatible"}:
        raise ValueError("Unsupported provider")
    if model is not None and (not model.strip() or len(model) > 120):
        raise ValueError("Invalid model")
    thread_id = uuid4().hex
    control.register(thread_id, principal.tenant_id, principal.user_id)
    initial = {"thread_id": thread_id, "tenant_id": principal.tenant_id, "user_id": principal.user_id,
               "role": principal.role, "question": question, "provider": provider,
               "model": model, "use_llm": use_llm, "rerank": rerank, "limit": limit}
    with open_graph() as graph:
        with deadline(float(os.getenv('WORKFLOW_DEADLINE_SECONDS', '120')),
                      cancelled=lambda: control.is_cancelled(thread_id)):
            graph.invoke(initial, config(thread_id))
        return view(graph.get_state(config(thread_id)))

def get_owned_snapshot(graph, thread_id: str, principal, *, reviewer=False):
    if not re.fullmatch(r"[0-9a-f]{32}", thread_id):
        raise LookupError("Workflow not found")
    snapshot = graph.get_state(config(thread_id))
    state = snapshot.values
    if not state or state.get("tenant_id") != principal.tenant_id:
        raise LookupError("Workflow not found")
    if reviewer:
        if principal.role not in {"admin", "editor"}:
            raise PermissionError("Reviewer role required")
    elif state.get("user_id") != principal.user_id and principal.role != "admin":
        raise LookupError("Workflow not found")
    return snapshot

def status(thread_id: str, principal) -> dict:
    with open_graph() as graph:
        return view(get_owned_snapshot(graph, thread_id, principal))

def decide(thread_id: str, principal, approved: bool) -> dict:
    if type(approved) is not bool:
        raise ValueError("approved must be boolean")
    with workflow_lock(thread_id), open_graph() as graph:
        snapshot = get_owned_snapshot(graph, thread_id, principal, reviewer=True)
        if control.is_cancelled(thread_id):
            raise ValueError('Workflow cancellation requested')
        if "approval" not in snapshot.next:
            raise ValueError("Workflow is not awaiting approval")
        with deadline(float(os.getenv("WORKFLOW_DEADLINE_SECONDS", "120")),
                      cancelled=lambda: control.is_cancelled(thread_id)):
            graph.invoke(Command(resume={"approved": approved, "reviewer_id": principal.user_id}),
                         config(thread_id))
        return view(graph.get_state(config(thread_id)))

def cancel(thread_id: str, principal) -> dict:
    with workflow_lock(thread_id), open_graph() as graph:
        snapshot = get_owned_snapshot(graph, thread_id, principal)
        if not snapshot.next:
            raise ValueError("Workflow already completed")
        return control.cancel(thread_id, principal.tenant_id, principal.user_id,
                              is_admin=principal.role == "admin")

def recovery_inventory(principal) -> list[dict]:
    """Read-only recovery inventory: does not auto-resume approvals or LLM calls."""
    if principal.role != "admin":
        raise PermissionError("Admin required")
    results = []
    for entry in control.inventory(principal.tenant_id):
        try:
            with open_graph() as graph:
                snapshot = get_owned_snapshot(graph, entry["thread_id"], principal)
                results.append({**entry, "workflow_status": view(snapshot)["status"]})
        except (LookupError, ValueError):
            results.append({**entry, "workflow_status": "checkpoint_missing"})
    return results
