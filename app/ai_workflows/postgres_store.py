"""Optional shared PostgreSQL LangGraph checkpointer for Sprint 2 prototype.

Install requirements-phase5-sprint2.txt and set WORKFLOW_CHECKPOINTER=postgres.
"""
from __future__ import annotations
import os
from contextlib import contextmanager
from langgraph.checkpoint.postgres import PostgresSaver

@contextmanager
def open_postgres_saver():
    url = os.environ.get("WORKFLOW_POSTGRES_URL") or os.environ.get("DATABASE_URL")
    if not url or not url.startswith(("postgresql://", "postgres://")):
        raise ValueError("WORKFLOW_POSTGRES_URL or PostgreSQL DATABASE_URL is required")
    with PostgresSaver.from_conn_string(url) as saver:
        # Idempotent schema initialization for prototype; run migrations separately in production.
        saver.setup()
        yield saver
