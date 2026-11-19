"""Extended learning API. Run: uvicorn app.lab_api:app --reload"""
import os
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from app.advanced import ask_advanced, add_text_document, price_tool
from app.evaluation import evaluate
from app.foundation.settings import get_settings
from app.foundation.logging import configure_logging, RequestLoggingMiddleware
from app.foundation.auth import current_principal, require_roles, Principal

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title='AriNova AI Engineering Lab — 10 Skills')
app.add_middleware(RequestLoggingMiddleware)

class Ask(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    session_id: str | None = None
    use_llm: bool = False

class Document(BaseModel):
    filename: str
    content: str

class Price(BaseModel):
    product: str
    quantity: int = 1
    discount_percent: float = 0

@app.get('/health')
def health():
    return {'status': 'ok', 'mode': 'learning'}

@app.post('/lab/ask')
def ask(payload: Ask, principal: Principal = Depends(current_principal)):
    raise HTTPException(status_code=410, detail='Legacy unscoped chat disabled; use /rag/answer')
    try:
        return ask_advanced(payload.question, payload.session_id, payload.use_llm)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='Model or retrieval unavailable') from exc

@app.post('/lab/documents')
def upload(payload: Document, x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    raise HTTPException(status_code=410, detail='Legacy shared document store disabled; use /rag/ingest')
    try:
        return add_text_document(payload.filename, payload.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post('/lab/price')
def price(payload: Price, x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    return price_tool(payload.product, payload.quantity, payload.discount_percent)

@app.get('/lab/evaluate')
def evals(x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    return evaluate()

# Persistent RAG is optional: install requirements-rag.txt to enable its routes.
try:
    from app.rag_api import router as rag_router
except ModuleNotFoundError as exc:
    if exc.name not in {"sqlalchemy", "pgvector", "sentence_transformers", "psycopg"}:
        raise
else:
    app.include_router(rag_router)
