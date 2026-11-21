"""Redis atomic replay reservation; same failed job can be replayed once.

A reservation is retained for 24 hours. The original RQ job is never mutated.
A failed enqueue may require admin investigation before another replay.
"""
from __future__ import annotations
import uuid

def reserve(redis, tenant, job_id):
    key = "arinova:replay:" + tenant + ":" + job_id
    token = uuid.uuid4().hex
    if not redis.set(key, token, nx=True, ex=86400):
        raise ValueError("Failed job already replayed or replay in progress")
    return key, token
