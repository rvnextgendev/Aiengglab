"""Tenant-scoped SQLite feedback for the integrated learning POC.

Keep free-text comments short; do not store the source document or answer.
"""
from __future__ import annotations
import os
import re
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

def _db():
    path = Path(os.getenv("WORKFLOW_FEEDBACK_SQLITE_PATH", ".data/workflow_feedback.sqlite"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=10)
    db.execute("""CREATE TABLE IF NOT EXISTS workflow_feedback (
        thread_id TEXT NOT NULL, tenant_id TEXT NOT NULL, user_id TEXT NOT NULL,
        rating INTEGER NOT NULL, comment TEXT NOT NULL, created_at TEXT NOT NULL,
        PRIMARY KEY(thread_id,tenant_id,user_id))""")
    return db

def submit(thread_id: str, tenant_id: str, user_id: str, rating: int, comment: str = "") -> dict:
    if not re.fullmatch(r"[0-9a-f]{32}", thread_id):
        raise ValueError("Invalid workflow ID")
    if type(rating) is not int or rating not in (1, 2, 3, 4, 5):
        raise ValueError("Rating must be between 1 and 5")
    if not isinstance(comment, str) or len(comment) > 500:
        raise ValueError("Comment must be at most 500 characters")
    with _db() as db:
        db.execute("""INSERT INTO workflow_feedback
            (thread_id,tenant_id,user_id,rating,comment,created_at)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(thread_id,tenant_id,user_id) DO UPDATE SET
            rating=excluded.rating,comment=excluded.comment,created_at=excluded.created_at""",
            (thread_id,tenant_id,user_id,rating,comment,
             datetime.now(timezone.utc).isoformat()))
    return {"thread_id": thread_id, "rating": rating, "saved": True}

def list_for_workflow(thread_id: str, tenant_id: str) -> list[dict]:
    with _db() as db:
        rows = db.execute("""SELECT user_id,rating,comment,created_at
            FROM workflow_feedback WHERE thread_id=? AND tenant_id=?
            ORDER BY created_at DESC""", (thread_id,tenant_id)).fetchall()
    return [{"user_id": r[0], "rating": r[1], "comment": r[2], "created_at": r[3]}
            for r in rows]
