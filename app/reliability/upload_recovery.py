"""Background reconciliation of orphaned Redis upload reservations.

Only remove a reservation when the corresponding RQ job is absent. Uses a
compare-and-delete Lua script to avoid deleting a replacement reservation.
"""
from app.reliability.ingestion_dedupe import upload_key

_DELETE_IF_SAME = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
"""

def reconcile_upload(redis, tenant, filename, data):
    key = upload_key(tenant, filename, data)
    job_id = redis.get(key)
    if not job_id:
        return {"status": "unreserved"}
    if isinstance(job_id, bytes):
        job_id = job_id.decode()
    from rq.job import Job
    from rq.exceptions import NoSuchJobError
    try:
        Job.fetch(job_id, connection=redis)
        return {"status": "tracked", "job_id": job_id}
    except NoSuchJobError:
        removed = redis.eval(_DELETE_IF_SAME, 1, key, job_id)
        return {"status": "orphan_cleared" if removed else "changed", "job_id": job_id}
