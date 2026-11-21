"""Redis RQ jobs. Queue payload is limited to 5 MB; protect Redis as sensitive storage."""
import os
from redis import Redis
from rq import Queue, Retry
from rq.job import Job
from app.advanced_rag.ingestion import ingest_file
from app.reliability.ingestion_dedupe import reserve_upload

def connection():
    return Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
                          socket_connect_timeout=3, socket_timeout=10)

def enqueue_document(tenant_id: str, filename: str, data: bytes) -> str:
    redis = connection()
    queue = Queue("arinova-ingestion", connection=redis, default_timeout=600)
    job_id, is_new = reserve_upload(redis, tenant_id, filename, data)
    if not is_new:
        return job_id
    job = queue.enqueue(ingest_file, tenant_id, filename, data,
                        job_id=job_id,
                        job_timeout=600, result_ttl=3600, failure_ttl=86400,
                        retry=Retry(max=3, interval=[10, 30, 90]))
    return job.id

def job_status(tenant_id: str, job_id: str) -> dict | None:
    job = Job.fetch(job_id, connection=connection())
    # RQ job arguments are trusted only because enqueue is authenticated and
    # the queue is private. Never expose job arguments to the client.
    if not job.args or job.args[0] != tenant_id:
        return None
    status = job.get_status(refresh=True)
    status_value = getattr(status, "value", str(status))
    return {"job_id": job.id, "status": status_value,
            "failed": status_value == "failed",
            "result": job.result if status_value == "finished" else None}
