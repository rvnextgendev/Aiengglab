from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.core import answer

app = FastAPI(title='AriNova AI Engineer Lab', version='0.1.0')

class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    use_llm: bool = False

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/ask')
def ask(payload: AskRequest):
    try:
        return answer(payload.question, payload.use_llm)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail='LLM service unavailable; try retrieval mode') from exc
