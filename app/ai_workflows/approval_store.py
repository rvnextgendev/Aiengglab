"""Sprint 2 prototype approval queue and audit trail in PostgreSQL.

This store tracks human decisions separately from LangGraph checkpoints.
"""
from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

def engine():
    url = os.getenv("WORKFLOW_POSTGRES_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("PostgreSQL URL required")
    return create_engine(url, pool_pre_ping=True)

def setup(db):
    db.execute(text("""CREATE TABLE IF NOT EXISTS workflow_approvals (
        thread_id VARCHAR(32) PRIMARY KEY,
        tenant_id VARCHAR(80) NOT NULL,
        owner_id VARCHAR(200) NOT NULL,
        status VARCHAR(30) NOT NULL,
        reviewer_id VARCHAR(200),
        reason TEXT,
        expires_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )"""))
    db.execute(text("""CREATE TABLE IF NOT EXISTS workflow_approval_events (
        id BIGSERIAL PRIMARY KEY,
        thread_id VARCHAR(32) NOT NULL,
        tenant_id VARCHAR(80) NOT NULL,
        actor_id VARCHAR(200) NOT NULL,
        action VARCHAR(40) NOT NULL,
        reason TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )"""))

def register(thread_id, tenant, owner, *, hours=24):
    expiry = datetime.now(timezone.utc) + timedelta(hours=hours)
    with Session(engine()) as db, db.begin():
        setup(db)
        db.execute(text("""INSERT INTO workflow_approvals
            (thread_id,tenant_id,owner_id,status,expires_at)
            VALUES (:thread,:tenant,:owner,'pending',:expiry)
            ON CONFLICT(thread_id) DO NOTHING"""),
            dict(thread=thread_id, tenant=tenant, owner=owner, expiry=expiry))

def pending(tenant, *, limit=50):
    with Session(engine()) as db:
        setup(db)
        rows = db.execute(text("""SELECT thread_id,owner_id,expires_at FROM workflow_approvals
            WHERE tenant_id=:tenant AND status='pending' AND expires_at>now()
            ORDER BY updated_at LIMIT :limit"""), {"tenant":tenant,"limit":min(max(limit,1),100)}).mappings()
        return [dict(r) for r in rows]

def decision(thread_id, tenant, reviewer, approved, reason=""):
    if not isinstance(approved, bool):
        raise ValueError("Decision must be boolean")
    action = "approved" if approved else "rejected"
    with Session(engine()) as db, db.begin():
        setup(db)
        row = db.execute(text("""UPDATE workflow_approvals SET status=:status,
             reviewer_id=:reviewer,reason=:reason,updated_at=now()
             WHERE thread_id=:thread AND tenant_id=:tenant AND status='pending'
               AND expires_at>now()
             RETURNING thread_id"""),
             dict(status=action, reviewer=reviewer, reason=reason, thread=thread_id, tenant=tenant)).first()
        if not row:
            raise ValueError("Approval unavailable, expired or already decided")
        db.execute(text("""INSERT INTO workflow_approval_events
            (thread_id,tenant_id,actor_id,action,reason)
            VALUES (:thread,:tenant,:reviewer,:action,:reason)"""),
            dict(thread=thread_id,tenant=tenant,reviewer=reviewer,action=action,reason=reason))
    return {"thread_id":thread_id,"status":action,"reviewer_id":reviewer}

def history(thread_id, tenant):
    with Session(engine()) as db:
        setup(db)
        rows = db.execute(text("""SELECT actor_id,action,reason,created_at
            FROM workflow_approval_events WHERE thread_id=:thread AND tenant_id=:tenant
            ORDER BY id"""),dict(thread=thread_id,tenant=tenant)).mappings()
        return [dict(r) for r in rows]
