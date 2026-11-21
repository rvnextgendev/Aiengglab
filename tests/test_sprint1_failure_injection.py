"""Offline failure-injection tests. Redis integration requires separate live tests."""
import pytest
from app.reliability.deadline import deadline, check, OperationCancelled
from app.reliability.workflow_control import register, cancel, is_cancelled, inventory
from app.reliability.resilience import retry_call, CircuitBreaker, CircuitOpen

def test_cancellation_flag(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKFLOW_CONTROL_PATH", str(tmp_path / "control.sqlite"))
    thread = "a" * 32
    register(thread, "tenant-A", "user-A")
    with pytest.raises(LookupError):
        cancel(thread, "tenant-B", "user-A")
    with pytest.raises(LookupError):
        cancel(thread, "tenant-A", "user-B")
    assert not is_cancelled(thread)
    assert cancel(thread, "tenant-A", "user-A")["cancel_requested"]
    assert is_cancelled(thread)
    assert inventory("tenant-A")[0]["thread_id"] == thread
    assert inventory("tenant-B") == []

def test_cancelled_deadline():
    with deadline(10, cancelled=lambda: True):
        with pytest.raises(OperationCancelled):
            check()

def test_expired_deadline():
    with deadline(0.001):
        import time
        time.sleep(0.01)
        with pytest.raises(TimeoutError):
            check()

def test_retry_stops_on_permanent_failure():
    calls = []
    def call():
        calls.append(1)
        raise ValueError("invalid input")
    with pytest.raises(ValueError):
        retry_call(call, retryable=lambda e: isinstance(e, TimeoutError),
                   attempts=3, sleep=lambda _: None)
    assert len(calls) == 1

def test_open_circuit_skips_calls():
    breaker = CircuitBreaker(failure_threshold=1)
    called = []
    def fail():
        called.append(1)
        raise TimeoutError("offline")
    with pytest.raises(TimeoutError):
        retry_call(fail, retryable=lambda e: True, attempts=1, breaker=breaker)
    with pytest.raises(CircuitOpen):
        retry_call(fail, retryable=lambda e: True, attempts=1, breaker=breaker)
    assert len(called) == 1
