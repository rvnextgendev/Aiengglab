"""Learn LangGraph checkpointing with print statements, no database needed."""
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict

class State(TypedDict, total=False):
    question: str
    answer: str

def prepare(state):
    print("Step 1: Received question:", state["question"])
    return {}

def approve(state):
    print("Step 2: Pausing for human approval")
    approved = interrupt({"question":state["question"],"message":"Approve?"})
    print("Step 3: Resumed. Decision:", approved)
    return {"answer":"Approved response" if approved else "Rejected by reviewer"}

builder = StateGraph(State)
builder.add_node("prepare",prepare)
builder.add_node("approve",approve)
builder.add_edge(START,"prepare")
builder.add_edge("prepare","approve")
builder.add_edge("approve",END)
graph = builder.compile(checkpointer=MemorySaver())
config = {"configurable":{"thread_id":"sprint2-print-example"}}
print("Starting workflow")
graph.invoke({"question":"Can AriNova answer this?"},config)
print("Saved checkpoint next step:",graph.get_state(config).next)
print("Reviewer approves")
graph.invoke(Command(resume=True),config)
print("Final answer:",graph.get_state(config).values["answer"])
