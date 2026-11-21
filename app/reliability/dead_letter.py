"""Tenant-scoped failed-job inspection and manual replay with explicit approval.

RQ FailedJobRegistry is the DLQ holding area. Replay uses original job function
and args only after allowlist and tenant checks. Do not expose serialized args.
"""
from __future__ import annotations
from rq import Queue, Retry
from rq.job import Job
from rq.registry import FailedJobRegistry
from app.advanced_rag.jobs import connection
from app.advanced_rag.ingestion import ingest_file

QUEUE = "arinova-ingestion"

def failed_jobs(tenant_id, limit=50):
    redis = connection()
    registry = FailedJobRegistry(QUEUE, connection=redis)
    results = []
    for job_id in registry.get_job_ids()[:min(max(limit, 1), 100)]:
        try:
            job = Job.fetch(job_id, connection=redis)
        except Exception:
            continue
        if job.func_name == f"{ingest_file.__module__}.{ingest_file.__name__}" and job.args and job.args[0] == tenant_id:
            results.append({"job_id": job.id, "status": "failed"})
    return results

def replay(tenant_id, job_id):
    redis = connection()
    registry = FailedJobRegistry(QUEUE, connection=redis)
    if job_id not in registry.get_job_ids():
        raise LookupError("Failed job not found")
    job = Job.fetch(job_id, connection=redis)
    if (job.func_name != f"{ingest_file.__module__}.{ingest_file.__name__}"
            or len(job.args) != 3 or job.args[0] != tenant_id
            or not isinstance(job.args[2], bytes) or len(job.args[2]) > 5 * 1024 * 1024):
        raise LookupError("Failed job not found")
    queue = Queue(QUEUE, connection=redis, default_timeout=600)
    new_job = queue.enqueue(ingest_file, *job.args, job_timeout=600,
                            result_ttl=3600, failure_ttl=86400,
                            retry=Retry(max=3, interval=[10, 30, 90]))
    return {"original_job_id": job.id, "replayed_job_id": new_job.id, "status": "queued"}
