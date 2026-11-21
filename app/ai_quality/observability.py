"""Minimal structured, non-sensitive workflow telemetry."""
import json
import logging
import time
from contextlib import contextmanager

logger = logging.getLogger("arinova.ai_quality")

@contextmanager
def measure(operation: str, *, provider: str = "none"):
    start = time.perf_counter()
    try:
        yield
    except Exception:
        logger.exception("ai_operation_failed", extra={"operation": operation})
        raise
    finally:
        logger.info(json.dumps({
            "event": "ai_operation",
            "operation": operation,
            "provider": provider,
            "duration_ms": round((time.perf_counter() - start) * 1000, 2)
        }))
