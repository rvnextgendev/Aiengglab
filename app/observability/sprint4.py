"""Sprint 4: lightweight privacy-preserving, tenant-scoped usage metrics."""
from __future__ import annotations
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def db():
    path = Path(os.getenv("AI_USAGE_SQLITE_PATH", ".data/ai_usage.sqlite"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS usage_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, tenant TEXT NOT NULL,
          operation TEXT NOT NULL, provider TEXT NOT NULL,
          latency_ms REAL NOT NULL, success INTEGER NOT NULL,
          estimated_input_tokens INTEGER NOT NULL,
          estimated_output_tokens INTEGER NOT NULL,
          created_at REAL NOT NULL)""")
        yield conn

def record(tenant, operation, provider, latency_ms, success,
           input_chars=0, output_chars=0):
    if not tenant or not operation or not provider:
        raise ValueError("Missing usage dimension")
    with db() as conn:
        conn.execute("""INSERT INTO usage_events
          (tenant,operation,provider,latency_ms,success,estimated_input_tokens,
           estimated_output_tokens,created_at)
          VALUES (?,?,?,?,?,?,?,?)""",
          (tenant,operation,provider,float(latency_ms),int(bool(success)),
           max(0,input_chars // 4),max(0,output_chars // 4),time.time()))

def summary(tenant, since_seconds=86400):
    with db() as conn:
        rows = conn.execute("""SELECT provider,COUNT(*),SUM(success),
           AVG(latency_ms),SUM(estimated_input_tokens),SUM(estimated_output_tokens)
           FROM usage_events WHERE tenant=? AND created_at>=?
           GROUP BY provider""",(tenant,time.time()-since_seconds)).fetchall()
    return [{"provider":r[0],"requests":r[1],"successful":r[2],
             "avg_latency_ms":round(r[3],2),
             "estimated_input_tokens":r[4],"estimated_output_tokens":r[5]}
            for r in rows]
