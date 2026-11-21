"""Atomic Redis admission for duplicate PDF upload requests.

The dedupe key is scoped to tenant, filename and file digest. A single Redis
reservation returns the original job id. If Redis is unavailable, fail closed.
"""
import hashlib
import uuid

def upload_key(tenant, filename, data):
    digest = hashlib.sha256(tenant.encode() + b"\x00" + filename.encode() + b"\x00" + data).hexdigest()
    return "arinova:upload:" + digest

def reserve_upload(redis, tenant, filename, data, *, ttl=86400):
    key = upload_key(tenant, filename, data)
    job_id = "ingest-" + uuid.uuid4().hex
    if redis.set(key, job_id, nx=True, ex=ttl):
        return job_id, True
    existing = redis.get(key)
    if not existing:
        raise RuntimeError("Upload reservation lost; retry safely")
    return existing.decode() if isinstance(existing, bytes) else existing, False
