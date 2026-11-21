"""Durable cancellation intent and recovery inventory for local SQLite workflows.

Cancellation is cooperative: a running external call cannot be forcibly terminated.
This control store is single-host only; use shared transactional storage in production.
"""
from __future__ import annotations
import os
import re
import sqlite3
import time
from pathlib import Path
from contextlib import contextmanager

def valid_thread(thread_id):
    if not re.fullmatch(r"[0-9a-f]{32}", thread_id):
        raise LookupError("Workflow not found")

@contextmanager
def store():
    path = Path(os.getenv("WORKFLOW_CONTROL_PATH", ".data/workflow_control.sqlite"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=10) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS controls (
            thread_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            user_id TEXT NOT NULL, cancelled INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL, updated_at REAL NOT NULL)""")
        yield db

def register(thread_id, tenant_id, user_id):
    valid_thread(thread_id)
    with store() as db:
        db.execute("INSERT OR IGNORE INTO controls VALUES (?, ?, ?, 0, ?, ?)",
                   (thread_id, tenant_id, user_id, time.time(), time.time()))

def cancel(thread_id, tenant_id, user_id, is_admin=False):
    valid_thread(thread_id)
    with store() as db:
        row = db.execute("SELECT tenant_id,user_id,cancelled FROM controls WHERE thread_id=?",
                         (thread_id,)).fetchone()
        if not row or row[0] != tenant_id or (row[1] != user_id and not is_admin):
            raise LookupError("Workflow not found")
        db.execute("UPDATE controls SET cancelled=1,updated_at=? WHERE thread_id=?",
                   (time.time(), thread_id))
        return {"thread_id": thread_id, "cancel_requested": True}

def is_cancelled(thread_id):
    valid_thread(thread_id)
    with store() as db:
        row = db.execute("SELECT cancelled FROM controls WHERE thread_id=?", (thread_id,)).fetchone()
        return bool(row and row[0])

def inventory(tenant_id, limit=100):
    with store() as db:
        rows = db.execute(
            "SELECT thread_id,cancelled,updated_at FROM controls WHERE tenant_id=? ORDER BY updated_at DESC LIMIT ?",
            (tenant_id, min(max(limit, 1), 100))).fetchall()
        return [{"thread_id": r[0], "cancel_requested": bool(r[1]), "updated_at": r[2]} for r in rows]
