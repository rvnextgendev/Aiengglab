"""Background document ingestion with page-aware chunks."""
import hashlib
import re
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.persistent_rag import RagDocument, RagChunk, embed, engine, split_text
from app.advanced_rag.extract import extract_pages

def ingest_file(tenant_id: str, filename: str, data: bytes) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", tenant_id):
        raise ValueError("Invalid tenant")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", filename) or filename.startswith("."):
        raise ValueError("Invalid filename")
    pages = extract_pages(filename, data)
    if not pages:
        raise ValueError("No extractable text (scanned PDFs need OCR)")
    chunks = [(page, chunk) for page, text in pages for chunk in split_text(text)]
    if len(chunks) > 1000:
        raise ValueError("Too many chunks")
    vectors = embed([chunk for _, chunk in chunks])
    digest = hashlib.sha256(data).hexdigest()
    with Session(engine()) as session:
        with session.begin():
            existing = session.scalar(select(RagDocument).where(
                RagDocument.tenant_id == tenant_id, RagDocument.filename == filename))
            if existing and existing.content_hash == digest:
                return {"filename": filename, "chunks": len(existing.chunks), "unchanged": True}
            if existing:
                session.delete(existing)
                session.flush()
            doc = RagDocument(tenant_id=tenant_id, filename=filename, content_hash=digest)
            doc.chunks = [
                RagChunk(chunk_index=i, page_number=page, content=text, embedding=vector)
                for i, ((page, text), vector) in enumerate(zip(chunks, vectors))
            ]
            session.add(doc)
    return {"filename": filename, "chunks": len(chunks), "unchanged": False}
