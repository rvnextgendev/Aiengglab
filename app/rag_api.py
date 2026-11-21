"""Authenticated, tenant-scoped persistent RAG endpoints."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header
from pydantic import BaseModel, Field
from app.foundation.auth import Principal, current_principal, require_roles
from app.persistent_rag import ingest, search
from app.rag_service import answer_question
from app.advanced_rag.jobs import enqueue_document, job_status
from app.advanced_rag.retrieval import hybrid_search
from app.advanced_rag.answer import hybrid_answer
from app.advanced_rag.extract import MAX_BYTES
from app.ai_workflows.graph import run_workflow
from app.ai_workflows import durable
from app.ai_quality.service import quality_answer
from app.reliability.idempotency import claim, complete, associate, IdempotencyConflict
from uuid import uuid4
from app.reliability import dead_letter

router = APIRouter(prefix="/rag", tags=["Persistent RAG"])

class IngestRequest(BaseModel):
    filename: str
    content: str

class SearchRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=3, ge=1, le=10)

class AnswerRequest(SearchRequest):
    use_llm: bool = True
    min_score: float = Field(default=0.35, ge=0, le=1)

@router.post("/ingest")
def ingest_document(payload: IngestRequest, principal: Principal = Depends(require_roles("admin", "editor"))):
    try:
        return ingest(principal.tenant_id, payload.filename, payload.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Persistent RAG unavailable") from exc

@router.post("/search")
def search_documents(payload: SearchRequest, principal: Principal = Depends(current_principal)):
    try:
        hits = search(principal.tenant_id, payload.question, payload.limit)
        return {"question": payload.question, "sources": hits,
                "answer": ("Relevant evidence: " + " | ".join(
                    f"[{hit['source']}] {hit['text']}" for hit in hits
                )) if hits else "I do not know based on the documents."}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Persistent RAG unavailable") from exc

@router.post("/answer")
def answer_documents(payload: AnswerRequest, principal: Principal = Depends(current_principal)):
    try:
        return answer_question(principal.tenant_id, payload.question, payload.use_llm,
                               payload.limit, payload.min_score)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Persistent RAG or Ollama unavailable") from exc

class HybridRequest(SearchRequest):
    rerank: bool = False

@router.post("/hybrid-search")
def hybrid_documents(payload: HybridRequest, principal: Principal = Depends(current_principal)):
    try:
        return {"question": payload.question,
                "sources": hybrid_search(principal.tenant_id, payload.question,
                                         payload.limit, payload.rerank)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Hybrid retrieval unavailable") from exc

@router.post("/upload", status_code=202)
async def upload_document(file: UploadFile = File(...),
                          principal: Principal = Depends(require_roles("admin", "editor"))):
    name = file.filename or ""
    if not name.lower().endswith((".pdf", ".txt")) or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="Invalid PDF/TXT filename")
    try:
        data = await file.read(MAX_BYTES + 1)
        if not data or len(data) > MAX_BYTES:
            raise HTTPException(status_code=413, detail="File must be 1 byte to 5 MB")
        job_id = enqueue_document(principal.tenant_id, name, data)
        return {"job_id": job_id, "status": "queued"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Ingestion queue unavailable") from exc
    finally:
        await file.close()

@router.get("/jobs/{job_id}")
def get_job(job_id: str, principal: Principal = Depends(current_principal)):
    if len(job_id) > 100 or not job_id.replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid job ID")
    try:
        result = job_status(principal.tenant_id, job_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Job queue unavailable") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return result

class HybridAnswerRequest(HybridRequest):
    use_llm: bool = True

@router.post("/hybrid-answer")
def answer_hybrid(payload: HybridAnswerRequest, principal: Principal = Depends(current_principal)):
    try:
        return hybrid_answer(principal.tenant_id, payload.question,
                             payload.limit, payload.rerank, payload.use_llm)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Hybrid answer unavailable") from exc

class WorkflowRequest(SearchRequest):
    provider: str = Field(default="ollama", pattern="^(ollama|openai-compatible)$")
    model: str | None = Field(default=None, max_length=120)
    use_llm: bool = True
    rerank: bool = False

@router.post("/workflow")
def run_ai_workflow(payload: WorkflowRequest,
                    principal: Principal = Depends(current_principal)):
    try:
        return run_workflow(principal.tenant_id, principal.role, payload.question,
                            payload.provider, payload.model, payload.use_llm,
                            payload.rerank, payload.limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="AI workflow unavailable") from exc

class ApprovalDecision(BaseModel):
    approved: bool
    reason: str = Field(default="", max_length=1000)

@router.post("/workflows", status_code=201)
def start_persistent_workflow(payload: WorkflowRequest,
                              principal: Principal = Depends(current_principal),
                              idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    try:
        if idempotency_key:
            existing = claim(principal.tenant_id, principal.user_id, "start_workflow",
                             idempotency_key, payload.model_dump())
            if not existing["new"]:
                if existing["status"] == "completed":
                    return existing["result"]
                if existing["result"] and existing["result"].get("thread_id"):
                    try:
                        recovered = durable.status(existing["result"]["thread_id"], principal)
                    except LookupError:
                        raise HTTPException(status_code=409, detail="Workflow checkpoint not yet available")
                    complete(principal.tenant_id, principal.user_id, "start_workflow", idempotency_key, recovered)
                    return recovered
                raise HTTPException(status_code=409, detail="Request is pending reconciliation")
        reserved_thread_id = uuid4().hex if idempotency_key else None
        if idempotency_key:
            associate(principal.tenant_id, principal.user_id, "start_workflow",
                      idempotency_key, {"thread_id": reserved_thread_id})
        result = durable.start(principal, payload.question, payload.provider,
                               payload.model, payload.use_llm, payload.rerank, payload.limit,
                               thread_id=reserved_thread_id)
        if idempotency_key:
            complete(principal.tenant_id, principal.user_id, "start_workflow", idempotency_key, result)
        return result
    except HTTPException:
        raise
    except IdempotencyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Persistent workflow unavailable") from exc

@router.get("/workflows/{thread_id}")
def get_persistent_workflow(thread_id: str,
                            principal: Principal = Depends(current_principal)):
    try:
        return durable.status(thread_id, principal)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Workflow not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Persistent workflow unavailable") from exc

@router.post("/workflows/{thread_id}/approval")
def approve_persistent_workflow(thread_id: str, payload: ApprovalDecision,
                                principal: Principal = Depends(require_roles("admin", "editor")),
                                idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    try:
        if idempotency_key:
            existing = claim(principal.tenant_id, principal.user_id, "approve:" + thread_id,
                             idempotency_key, payload.model_dump())
            if not existing["new"]:
                if existing["status"] == "completed":
                    return existing["result"]
                try:
                    recovered = durable.status(thread_id, principal)
                except LookupError:
                    raise HTTPException(status_code=409, detail="Approval checkpoint unavailable")
                if recovered["status"] == "completed":
                    complete(principal.tenant_id, principal.user_id, "approve:" + thread_id,
                             idempotency_key, recovered)
                    return recovered
                raise HTTPException(status_code=409, detail="Approval pending reconciliation")
        result = durable.decide(thread_id, principal, payload.approved, payload.reason)
        if idempotency_key:
            complete(principal.tenant_id, principal.user_id, "approve:" + thread_id,
                     idempotency_key, result)
        return result
    except HTTPException:
        raise
    except IdempotencyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Workflow not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="Reviewer role required") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Persistent workflow unavailable") from exc

@router.post("/workflows/{thread_id}/cancel")
def cancel_persistent_workflow(thread_id: str,
                              principal: Principal = Depends(current_principal)):
    try:
        return durable.cancel(thread_id, principal)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Workflow not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Cancellation unavailable") from exc

@router.get("/workflows-recovery")
def list_workflows_for_recovery(principal: Principal = Depends(require_roles("admin"))):
    return {"workflows": durable.recovery_inventory(principal)}

@router.get("/failed-jobs")
def list_failed_jobs(principal: Principal = Depends(require_roles("admin"))):
    return {"jobs": dead_letter.failed_jobs(principal.tenant_id)}

@router.post("/failed-jobs/{job_id}/replay", status_code=202)
def replay_failed_job(job_id: str,
                      principal: Principal = Depends(require_roles("admin"))):
    try:
        return dead_letter.replay(principal.tenant_id, job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Failed job not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Failed-job replay unavailable") from exc

@router.post("/quality-answer")
def answer_with_quality_gate(payload: WorkflowRequest,
                             principal: Principal = Depends(current_principal)):
    try:
        return quality_answer(principal.tenant_id, payload.question,
                              payload.provider, payload.model, payload.limit,
                              payload.rerank, payload.use_llm)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Quality-gated answer unavailable") from exc

@router.get("/approval-queue")
def approval_queue(principal: Principal = Depends(require_roles("admin", "editor"))):
    from app.ai_workflows import approval_store
    try:
        return {"items": approval_store.pending(principal.tenant_id)}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Approval queue unavailable") from exc

@router.get("/workflows/{thread_id}/approval-history")
def workflow_approval_history(thread_id: str,
                              principal: Principal = Depends(current_principal)):
    from app.ai_workflows import approval_store
    try:
        durable.status(thread_id, principal)
        return {"events": approval_store.history(thread_id, principal.tenant_id)}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Workflow not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Approval history unavailable") from exc
