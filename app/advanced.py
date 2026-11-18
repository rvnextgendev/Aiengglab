"""Advanced learning workflow: semantic RAG, tools, sessions, tracing."""
from __future__ import annotations
import json, os, re, time, uuid
from pathlib import Path
from typing import Any
from app.core import DOC_PATH, safe_question, ollama_answer

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / 'data' / 'uploads'
STORE.mkdir(parents=True, exist_ok=True)
SESSIONS: dict[str, list[dict]] = {}

def documents() -> list[dict]:
    paths = [DOC_PATH, *sorted(STORE.glob('*.txt'))]
    out = []
    for path in paths:
        content = path.read_text(encoding='utf-8')
        for i, line in enumerate(content.splitlines(), 1):
            if line.strip():
                out.append({'source': f'{path.name}:L{i}', 'text': line.strip()})
    return out

def semantic_search(query: str, limit: int = 3) -> list[dict]:
    """Optional local embeddings; fallback keyword ranking for lightweight installs."""
    docs = documents()
    if not docs: return []
    try:
        from sentence_transformers import SentenceTransformer, util
        model = SentenceTransformer(os.getenv('EMBED_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'))
        corpus = model.encode([d['text'] for d in docs], convert_to_tensor=True)
        q = model.encode(query, convert_to_tensor=True)
        scores = util.cos_sim(q, corpus)[0].tolist()
        ranked = sorted(zip(docs, scores), key=lambda pair: pair[1], reverse=True)
        return [{**doc, 'score': round(float(score), 4)} for doc, score in ranked[:limit] if score >= 0.20]
    except ImportError:
        words = set(re.findall(r'[a-z0-9]+', query.lower())) - {'how','what','the','a','is','are','can','i','you','me'}
        ranked = sorted(((d, len(words & set(re.findall(r'[a-z0-9]+', d['text'].lower())))) for d in docs), key=lambda pair: pair[1], reverse=True)
        return [{**d, 'score': score} for d, score in ranked[:limit] if score]

CATALOG = {'starter': 2000, 'premium': 4500}

def price_tool(product: str, quantity: int = 1, discount_percent: float = 0) -> dict:
    if product not in CATALOG: raise ValueError('Unknown product')
    if not 1 <= quantity <= 100: raise ValueError('Quantity must be between 1 and 100')
    if not 0 <= discount_percent <= 50: raise ValueError('Discount must be 0 to 50 percent')
    return {'product': product, 'quantity': quantity, 'discount_percent': discount_percent,
            'total_inr': round(CATALOG[product] * quantity * (1 - discount_percent / 100), 2)}

def route(question: str) -> str:
    q = question.lower()
    if re.search(r'\b(price|cost|total|discount|calculate)\b', q) and re.search(r'\b(starter|premium)\b', q):
        return 'price_tool'
    return 'document_search'

def ask_advanced(question: str, session_id: str | None = None, use_llm: bool = False) -> dict:
    start = time.perf_counter()
    question = safe_question(question)
    session_id = session_id or uuid.uuid4().hex
    history = SESSIONS.setdefault(session_id, [])
    if len(history) >= 20: history[:] = history[-18:]
    tool = route(question)
    sources = []
    if tool == 'price_tool':
        product = 'premium' if 'premium' in question.lower() else 'starter'
        match = re.search(r'\b(\d+)\s*(?:items?|pairs?|units?)\b', question.lower())
        quantity = int(match.group(1)) if match else 1
        discount = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:discount|off)', question.lower())
        data = price_tool(product, quantity, float(discount.group(1)) if discount else 0)
        response = f"Calculated price: INR {data['total_inr']:,.2f} for {data['quantity']} {product} item(s), with {data['discount_percent']}% discount."
    else:
        hits = semantic_search(question)
        sources = [{'source': d['source'], 'score': d['score'], 'text': d['text']} for d in hits]
        if not hits:
            response = 'I do not know based on the documents.'
        elif use_llm:
            response = ollama_answer(question, hits)
        else:
            response = 'Relevant evidence: ' + ' | '.join(f"[{d['source']}] {d['text']}" for d in hits)
    history.append({'question': question, 'answer': response})
    result = {'session_id': session_id, 'answer': response, 'tool': tool,
              'sources': sources, 'history_length': len(history),
              'latency_ms': round((time.perf_counter() - start) * 1000, 2)}
    with (ROOT / 'events.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps({'event': 'advanced_question', **result}) + '\n')
    return result

def add_text_document(filename: str, content: str) -> dict:
    name = Path(filename).name
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,60}\.txt', name):
        raise ValueError('Only safe .txt filenames are allowed')
    if not content.strip() or len(content.encode('utf-8')) > 100_000:
        raise ValueError('Document must be nonempty and <=100 KB')
    path = STORE / name
    path.write_text(content, encoding='utf-8')
    return {'filename': name, 'characters': len(content)}
