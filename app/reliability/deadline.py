"""Cooperative deadlines and cancellation for long-running workflows."""
from __future__ import annotations
import contextvars
import time
from contextlib import contextmanager
from dataclasses import dataclass

_current = contextvars.ContextVar("arinova_deadline", default=None)

class OperationCancelled(RuntimeError):
    pass

@dataclass(frozen=True)
class Deadline:
    expires_at: float
    cancelled: object | None = None

    def remaining(self) -> float:
        self.check()
        return max(0.0, self.expires_at - time.monotonic())

    def check(self):
        if self.cancelled is not None and self.cancelled():
            raise OperationCancelled("Operation cancelled")
        if time.monotonic() >= self.expires_at:
            raise TimeoutError("Operation deadline exceeded")

@contextmanager
def deadline(seconds: float, cancelled=None):
    if not 0 < seconds <= 3600:
        raise ValueError("Deadline must be between 0 and 3600 seconds")
    parent = _current.get()
    expiry = min(time.monotonic() + seconds, parent.expires_at) if parent else time.monotonic() + seconds
    ctx = Deadline(expiry, cancelled or (parent.cancelled if parent else None))
    token = _current.set(ctx)
    try:
        yield ctx
    finally:
        _current.reset(token)

def current_deadline():
    return _current.get()

def check():
    ctx = current_deadline()
    if ctx:
        ctx.check()
