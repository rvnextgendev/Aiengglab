import pytest
from app.reliability.ingestion_dedupe import reserve_upload
from app.reliability.deadline import deadline, check, OperationCancelled

class FakeRedis:
    def __init__(self):
        self.values = {}
    def set(self, key, value, nx, ex):
        if key in self.values:
            return False
        self.values[key] = value
        return True
    def get(self, key):
        return self.values.get(key)

def test_upload_dedupe_tenant_and_content():
    redis = FakeRedis()
    first, new = reserve_upload(redis, "tenant1", "doc.pdf", b"one")
    assert new
    second, new = reserve_upload(redis, "tenant1", "doc.pdf", b"one")
    assert not new and second == first
    third, new = reserve_upload(redis, "tenant2", "doc.pdf", b"one")
    assert new and third != first
    fourth, new = reserve_upload(redis, "tenant1", "doc.pdf", b"two")
    assert new and fourth != first

def test_cooperative_cancellation():
    with deadline(10, cancelled=lambda: True):
        with pytest.raises(OperationCancelled):
            check()
