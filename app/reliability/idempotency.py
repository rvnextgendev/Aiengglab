"""SQLite-backed idempotency for local single-instance development.

Atomic claim avoids duplicate starts; pending claims must be reconciled after a crash.
"""
import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

class IdempotencyConflict(ValueError):
    pass

@contextmanager
def database():
    path = Path(os.getenv("IDEMPOTENCY_SQLITE_PATH", ".data/idempotency.sqlite"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path), timeout=10) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS claims (
            tenant TEXT NOT NULL, actor TEXT NOT NULL, operation TEXT NOT NULL,
            key TEXT NOT NULL, fingerprint TEXT NOT NULL, status TEXT NOT NULL,
            result TEXT, created_at REAL NOT NULL,
            PRIMARY KEY (tenant, actor, operation, key))""")
        yield db

def fingerprint(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def claim(tenant: str, actor: str, operation: str, key: str, payload: dict):
    if not 8 <= len(key) <= 128 or not all(c.isalnum() or c in "-_" for c in key):
        raise ValueError("Invalid idempotency key")
    digest = fingerprint(payload)
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT fingerprint, status, result FROM claims WHERE tenant=? AND actor=? AND operation=? AND key=?",
            (tenant, actor, operation, key)).fetchone()
        if row:
            if row[0] != digest:
                raise IdempotencyConflict("Key already used with a different request")
            return {"new": False, "status": row[1], "result": json.loads(row[2]) if row[2] else None}
        db.execute("INSERT INTO claims VALUES (?, ?, ?, ?, ?, 'pending', NULL, ?)",
                   (tenant, actor, operation, key, digest, time.time()))
        return {"new": True, "status": "pending", "result": None}

def complete(tenant: str, actor: str, operation: str, key: str, result: dict):
    with database() as db:
        db.execute("UPDATE claims SET status='completed', result=? WHERE tenant=? AND actor=? AND operation=? AND key=? AND status='pending'",
                   (json.dumps(result), tenant, actor, operation, key))
