"""Authenticated, tenant-scoped persistent RAG endpoints."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from app.foundation.auth import Principal, current_principal, require_roles
from app.persistent_rag import ingest, search
from app.rag_service import answer_question
from app.advanced_rag.jobs import enqueue_document, job_status
from app.advanced_rag.retrieval import hybrid_search
from app.advanced_rag.extract import MAX_BYTES

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
