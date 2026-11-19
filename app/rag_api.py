"""Authenticated, tenant-scoped persistent RAG endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.foundation.auth import Principal, current_principal, require_roles
from app.persistent_rag import ingest, search
from app.rag_service import answer_question

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
