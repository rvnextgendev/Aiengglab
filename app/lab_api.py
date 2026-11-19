"""Extended learning API. Run: uvicorn app.lab_api:app --reload"""
import os
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
from app.advanced import ask_advanced, add_text_document, price_tool
from app.evaluation import evaluate

app = FastAPI(title='AriNova AI Engineering Lab — 10 Skills')

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

def require_key(x_api_key: str | None):
    expected = os.getenv('LAB_API_KEY')
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail='Invalid API key')

@app.get('/health')
def health():
    return {'status': 'ok', 'mode': 'learning'}

@app.post('/lab/ask')
def ask(payload: Ask, x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    try:
        return ask_advanced(payload.question, payload.session_id, payload.use_llm)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='Model or retrieval unavailable') from exc

@app.post('/lab/documents')
def upload(payload: Document, x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    try:
        return add_text_document(payload.filename, payload.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post('/lab/price')
def price(payload: Price, x_api_key: str | None = Header(default=None)):
    require_key(x_api_key)
    try:
        return price_tool(payload.product, payload.quantity, payload.discount_percent)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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
