"""Bounded retries with jitter, circuit breaker, and explicit deadlines."""
from __future__ import annotations
import random
import threading
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

T = TypeVar("T")

class CircuitOpen(RuntimeError):
    pass

@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_seconds: float = 30.0

    def __post_init__(self):
        if self.failure_threshold < 1 or self.recovery_seconds <= 0:
            raise ValueError("Invalid circuit breaker configuration")
        self._failures = 0
        self._opened_at: float | None = None
        self._probe = False
        self._lock = threading.Lock()

    def before_call(self):
        with self._lock:
            if self._opened_at is None:
                return
            if time.monotonic() - self._opened_at < self.recovery_seconds:
                raise CircuitOpen("Provider circuit is open")
            if self._probe:
                raise CircuitOpen("Provider recovery probe in progress")
            self._probe = True

    def success(self):
        with self._lock:
            self._failures = 0
            self._opened_at = None
            self._probe = False

    def failure(self):
        with self._lock:
            self._failures += 1
            if self._probe or self._failures >= self.failure_threshold:
                self._opened_at = time.monotonic()
            self._probe = False

    def release_probe(self):
        with self._lock:
            self._probe = False

def retry_call(fn: Callable[[], T], *, retryable: Callable[[Exception], bool],
               attempts: int = 3, base_delay: float = 0.2,
               max_delay: float = 3.0, deadline_seconds: float = 60.0,
               breaker: CircuitBreaker | None = None,
               sleep: Callable[[float], None] = time.sleep) -> T:
    if not 1 <= attempts <= 5 or base_delay < 0 or max_delay < 0 or deadline_seconds <= 0:
        raise ValueError("Invalid retry settings")
    end = time.monotonic() + deadline_seconds
    for attempt in range(attempts):
        if time.monotonic() >= end:
            raise TimeoutError("Operation deadline exceeded")
        if breaker:
            breaker.before_call()
        try:
            result = fn()
        except Exception as exc:
            if not retryable(exc):
                if breaker:
                    breaker.release_probe()
                raise
            if breaker:
                breaker.failure()
            if attempt == attempts - 1:
                raise
            remaining = end - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Operation deadline exceeded") from exc
            delay = min(max_delay, base_delay * (2 ** attempt))
            sleep(min(remaining, random.uniform(0, delay)))
        else:
            if breaker:
                breaker.success()
            return result
    raise AssertionError("Unreachable")
