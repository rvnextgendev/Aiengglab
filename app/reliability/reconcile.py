"""Safe idempotency reconciliation: never re-execute a possibly completed side effect."""
import json
import time
from app.reliability.idempotency import database

def pending_claims(tenant, older_than_seconds=300, limit=100):
    if older_than_seconds < 0:
        raise ValueError("Invalid age")
    with database() as db:
        rows = db.execute("""SELECT actor,operation,key,created_at FROM claims
          WHERE tenant=? AND status='pending' AND created_at<=?
          ORDER BY created_at LIMIT ?""",
          (tenant, time.time()-older_than_seconds, min(max(limit, 1), 100))).fetchall()
    return [{"actor": r[0], "operation": r[1], "key": r[2], "created_at": r[3]} for r in rows]

def reconcile_workflow_claim(tenant, actor, key, principal):
    """Reconcile only if a single matching durable workflow is found.

    Never auto-create or re-run an unknown workflow. Caller must supply the
    original authorized principal; cross-tenant data is not returned.
    """
    from app.ai_workflows import durable
    from app.reliability import workflow_control
    with database() as db:
        row = db.execute("SELECT fingerprint,status,result FROM claims WHERE tenant=? AND actor=? AND operation='start_workflow' AND key=?",
                         (tenant, actor, key)).fetchone()
        if not row:
            raise LookupError("Claim not found")
        if row[1] == "completed":
            return json.loads(row[2])
    # No safe mapping from request key to workflow id in the legacy schema.
    # Return explicit unresolved status; do not guess or repeat side effects.
    return {"status": "requires_manual_reconciliation", "operation": "start_workflow", "key": key}
