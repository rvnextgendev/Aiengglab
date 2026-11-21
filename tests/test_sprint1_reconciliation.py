import pytest
from app.reliability.idempotency import claim
from app.reliability.reconcile import pending_claims, reconcile_workflow_claim
from app.reliability.replay_lock import reserve

def test_pending_claim_does_not_auto_execute(tmp_path, monkeypatch):
    monkeypatch.setenv("IDEMPOTENCY_SQLITE_PATH", str(tmp_path / "claims.sqlite"))
    claim("tenant1", "actor1", "start_workflow", "request-0001", {"question": "A"})
    rows = pending_claims("tenant1", older_than_seconds=0)
    assert len(rows) == 1
    assert pending_claims("tenant2", older_than_seconds=0) == []
    result = reconcile_workflow_claim("tenant1", "actor1", "request-0001", None)
    assert result["status"] == "requires_manual_reconciliation"

def test_replay_reservation_prevents_duplicates():
    class FakeRedis:
        def __init__(self):
            self.values = {}
        def set(self, key, value, nx, ex):
            if key in self.values:
                return False
            self.values[key] = value
            return True
    redis = FakeRedis()
    reserve(redis, "tenant", "job1")
    with pytest.raises(ValueError):
        reserve(redis, "tenant", "job1")
