"""Persistent TXT retrieval using PostgreSQL/pgvector and local embeddings."""
from __future__ import annotations
import hashlib
import os
import re
from functools import lru_cache

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship
from pgvector.sqlalchemy import VECTOR

EMBED_DIM = 384
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

class Base(DeclarativeBase):
    pass

class RagDocument(Base):
    __tablename__ = "rag_documents"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(80), index=True)
    filename: Mapped[str] = mapped_column(String(100))
    content_hash: Mapped[str] = mapped_column(String(64))
    chunks: Mapped[list["RagChunk"]] = relationship(cascade="all, delete-orphan", back_populates="document")
    __table_args__ = (Index("ix_rag_document_unique", "tenant_id", "filename", unique=True),)

class RagChunk(Base):
    __tablename__ = "rag_chunks"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("rag_documents.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(VECTOR(EMBED_DIM))
    document: Mapped[RagDocument] = relationship(back_populates="chunks")
    __table_args__ = (Index("ix_rag_chunks_embedding_hnsw", "embedding", postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"}),)

@lru_cache(maxsize=1)
def engine():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required for persistent RAG")
    return create_engine(url, pool_pre_ping=True)

@lru_cache(maxsize=1)
def embedding_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)

def embed(texts: list[str]) -> list[list[float]]:
    vectors = embedding_model().encode(texts, normalize_embeddings=True)
    return vectors.tolist()

def split_text(content: str, chunk_size: int = 600, overlap: int = 100) -> list[str]:
    if chunk_size <= overlap or overlap < 0:
        raise ValueError("Invalid chunk configuration")
    normalized = re.sub(r"\s+", " ", content).strip()
    if not normalized:
        return []
    result = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        result.append(normalized[start:end])
        if end == len(normalized):
            break
        start = end - overlap
    return result

def ingest(tenant_id: str, filename: str, content: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", tenant_id):
        raise ValueError("Invalid tenant ID")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,60}\.txt", filename):
        raise ValueError("Only safe TXT filenames are supported")
    if not content.strip() or len(content.encode("utf-8")) > 100_000:
        raise ValueError("Document must be nonempty and <=100 KB")
    chunks = split_text(content)
    vectors = embed(chunks)
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    with Session(engine()) as session:
        with session.begin():
            existing = session.scalar(select(RagDocument).where(
                RagDocument.tenant_id == tenant_id,
                RagDocument.filename == filename
            ))
            if existing and existing.content_hash == digest:
                return {"filename": filename, "chunks": len(existing.chunks), "unchanged": True}
            if existing:
                session.delete(existing)
                session.flush()
            doc = RagDocument(tenant_id=tenant_id, filename=filename, content_hash=digest)
            doc.chunks = [RagChunk(chunk_index=i, content=chunk, embedding=vector)
                          for i, (chunk, vector) in enumerate(zip(chunks, vectors))]
            session.add(doc)
    return {"filename": filename, "chunks": len(chunks), "unchanged": False}

def search(tenant_id: str, question: str, limit: int = 3) -> list[dict]:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", tenant_id):
        raise ValueError("Invalid tenant ID")
    if not question.strip() or len(question) > 500:
        raise ValueError("Invalid question")
    if not 1 <= limit <= 10:
        raise ValueError("Limit must be 1 to 10")
    vector = embed([question])[0]
    distance = RagChunk.embedding.cosine_distance(vector)
    with Session(engine()) as session:
        rows = session.execute(
            select(RagChunk, RagDocument.filename, distance.label("distance"))
            .join(RagDocument)
            .where(RagDocument.tenant_id == tenant_id)
            .order_by(distance)
            .limit(limit)
        ).all()
    return [{"source": f"{filename}:chunk-{chunk.chunk_index}", "text": chunk.content,
             "score": round(1 - float(dist), 4)} for chunk, filename, dist in rows]
