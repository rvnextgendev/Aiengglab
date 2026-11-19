"""Authenticated AriNova lab API."""
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.advanced import price_tool
from app.evaluation import evaluate
from app.foundation.settings import get_settings
from app.foundation.logging import configure_logging, RequestLoggingMiddleware
from app.foundation.auth import current_principal, require_roles, Principal

settings = get_settings()
configure_logging(settings.log_level)
app = FastAPI(title="AriNova AI Engineering Lab")
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

@app.get("/health")
def health():
    return {"status": "ok", "mode": "foundation"}

@app.post("/lab/ask", status_code=410)
def old_chat(payload: Ask, principal: Principal = Depends(current_principal)):
    raise HTTPException(status_code=410, detail="Legacy unscoped chat disabled; use /rag/answer")

@app.post("/lab/documents", status_code=410)
def old_upload(payload: Document, principal: Principal = Depends(require_roles("admin", "editor"))):
    raise HTTPException(status_code=410, detail="Legacy shared document store disabled; use /rag/ingest")

@app.post("/lab/price")
def price(payload: Price, principal: Principal = Depends(current_principal)):
    try:
        return price_tool(payload.product, payload.quantity, payload.discount_percent)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/lab/evaluate")
def evals(principal: Principal = Depends(require_roles("admin"))):
    return evaluate()

from app.rag_api import router as rag_router
app.include_router(rag_router)
