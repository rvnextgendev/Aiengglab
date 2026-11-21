"""Tenant-filtered pgvector + PostgreSQL full-text search, RRF and optional reranking."""
from functools import lru_cache
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.persistent_rag import RagChunk, RagDocument, embed, engine

def reciprocal_rank_fusion(lists: list[list[dict]], k: int = 60) -> list[dict]:
    combined = {}
    for results in lists:
        for rank, hit in enumerate(results, 1):
            key = hit["id"]
            if key not in combined:
                combined[key] = {**hit, "score": 0.0}
            combined[key]["score"] += 1.0 / (k + rank)
    return sorted(combined.values(), key=lambda hit: hit["score"], reverse=True)

@lru_cache(maxsize=1)
def reranker():
    from sentence_transformers import CrossEncoder
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank(question: str, hits: list[dict], limit: int) -> list[dict]:
    if not hits:
        return []
    scores = reranker().predict([(question, hit["text"]) for hit in hits])
    return [{**hit, "score": float(score)} for hit, score in
            sorted(zip(hits, scores), key=lambda item: float(item[1]), reverse=True)[:limit]]

def hybrid_search(tenant_id: str, question: str, limit: int = 3,
                  use_reranker: bool = False) -> list[dict]:
    if not tenant_id or len(tenant_id) > 80:
        raise ValueError("Invalid tenant")
    if not question.strip() or len(question) > 500 or not 1 <= limit <= 10:
        raise ValueError("Invalid search request")
    candidates = min(50, max(10, limit * 5))
    query_vector = embed([question])[0]
    distance = RagChunk.embedding.cosine_distance(query_vector)
    tsv = func.to_tsvector("english", RagChunk.content)
    tsq = func.plainto_tsquery("english", question)
    rank = func.ts_rank_cd(tsv, tsq)
    with Session(engine()) as session:
        base = (select(RagChunk.id, RagChunk.content, RagChunk.chunk_index,
                       RagChunk.page_number, RagDocument.filename)
                .join(RagDocument)
                .where(RagDocument.tenant_id == tenant_id))
        semantic = session.execute(base.order_by(distance).limit(candidates)).all()
        lexical = session.execute(base.where(tsv.op("@@")(tsq))
                                  .order_by(rank.desc()).limit(candidates)).all()
    def convert(rows):
        return [{"id": row.id, "text": row.content,
                 "source": f"{row.filename}:page-{row.page_number or 1}:chunk-{row.chunk_index}"}
                for row in rows]
    fused = reciprocal_rank_fusion([convert(semantic), convert(lexical)])
    if use_reranker:
        return rerank(question, fused[:candidates], limit)
    return fused[:limit]
