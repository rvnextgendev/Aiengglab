import pytest
from app.reliability.resilience import CircuitBreaker, CircuitOpen, retry_call
from app.reliability.idempotency import claim, complete, IdempotencyConflict

def test_retry_transient():
    calls = []
    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise TimeoutError()
        return "ok"
    assert retry_call(flaky, retryable=lambda e: isinstance(e, TimeoutError),
                      attempts=3, sleep=lambda _: None) == "ok"
    assert len(calls) == 3

def test_no_retry_permanent():
    with pytest.raises(ValueError):
        retry_call(lambda: (_ for _ in ()).throw(ValueError("bad")),
                   retryable=lambda e: isinstance(e, TimeoutError),
                   sleep=lambda _: None)

def test_circuit_opens():
    breaker = CircuitBreaker(failure_threshold=2)
    for _ in range(2):
        with pytest.raises(TimeoutError):
            retry_call(lambda: (_ for _ in ()).throw(TimeoutError()),
                       retryable=lambda e: True, attempts=1, breaker=breaker)
    with pytest.raises(CircuitOpen):
        breaker.before_call()

def test_idempotency(tmp_path, monkeypatch):
    monkeypatch.setenv("IDEMPOTENCY_SQLITE_PATH", str(tmp_path / "idempotency.sqlite"))
    key = "request-1234"
    assert claim("tenant", "user", "start", key, {"question": "hi"})["new"]
    complete("tenant", "user", "start", key, {"thread_id": "abc"})
    again = claim("tenant", "user", "start", key, {"question": "hi"})
    assert not again["new"]
    assert again["result"]["thread_id"] == "abc"
    with pytest.raises(IdempotencyConflict):
        claim("tenant", "user", "start", key, {"question": "different"})
