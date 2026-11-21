"""Offline LangGraph checkpoint and human approval demo tests."""
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict

class State(TypedDict, total=False):
    question: str
    result: str

def test_pause_and_resume():
    def gate(state):
        approved = interrupt("Approve?")
        return {"result": "yes" if approved else "no"}
    builder = StateGraph(State)
    builder.add_node("gate",gate)
    builder.add_edge(START,"gate")
    builder.add_edge("gate",END)
    graph = builder.compile(checkpointer=MemorySaver())
    cfg = {"configurable":{"thread_id":"sprint2-test"}}
    graph.invoke({"question":"Test"},cfg)
    assert "gate" in graph.get_state(cfg).next
    graph.invoke(Command(resume=True),cfg)
    assert graph.get_state(cfg).values["result"] == "yes"
