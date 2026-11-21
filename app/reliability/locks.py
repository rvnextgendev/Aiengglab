"""Cross-process per-workflow lock for local single-host SQLite deployment."""
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def workflow_lock(thread_id, *, timeout=20):
    path = Path(os.getenv("WORKFLOW_LOCK_PATH", ".data/workflow_locks.sqlite"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=timeout, isolation_level=None)
    try:
        db.execute("PRAGMA busy_timeout = " + str(int(timeout * 1000)))
        db.execute("BEGIN IMMEDIATE")
        # SQLite holds a database-wide writer lock until graph resume completes.
        # Safe for single-host pilot; replace with per-thread Postgres advisory locks.
        yield
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    finally:
        db.close()
