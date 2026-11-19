"""Opt-in persistent RAG endpoints; tenant is fixed by server configuration."""
import os
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from app.persistent_rag import ingest, search, initialize

router = APIRouter(prefix="/rag", tags=["Persistent RAG"])

class IngestRequest(BaseModel):
    filename: str
    content: str

class SearchRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=3, ge=1, le=10)

def authorize(api_key: str | None):
    expected = os.getenv("LAB_API_KEY")
    if not expected or api_key != expected:
        raise HTTPException(status_code=401, detail="Configure LAB_API_KEY and supply X-API-Key")

def tenant() -> str:
    # Single-tenant learning demo. Do NOT trust tenant IDs supplied by clients.
    return os.getenv("RAG_TENANT_ID", "arinova-demo")

@router.post("/ingest")
def ingest_document(payload: IngestRequest, x_api_key: str | None = Header(default=None)):
    authorize(x_api_key)
    try:
        return ingest(tenant(), payload.filename, payload.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Persistent RAG unavailable") from exc

@router.post("/search")
def search_documents(payload: SearchRequest, x_api_key: str | None = Header(default=None)):
    authorize(x_api_key)
    try:
        hits = search(tenant(), payload.question, payload.limit)
        return {"question": payload.question, "sources": hits,
                "answer": ("Relevant evidence: " + " | ".join(
                    f"[{hit['source']}] {hit['text']}" for hit in hits
                )) if hits else "I do not know based on the documents."}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Persistent RAG unavailable") from exc

@router.post("/initialize")
def initialize_database(x_api_key: str | None = Header(default=None)):
    authorize(x_api_key)
    try:
        initialize()
        return {"status": "initialized"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database initialization failed") from exc
