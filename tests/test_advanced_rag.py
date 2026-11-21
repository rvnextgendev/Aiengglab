"""Offline advanced RAG tests; no model downloads or database."""
from io import BytesIO
from pypdf import PdfWriter
import pytest
from app.advanced_rag.extract import extract_pages
from app.advanced_rag.retrieval import reciprocal_rank_fusion

def test_txt_extract():
    assert extract_pages("policy.txt", b"14 day return") == [(1, "14 day return")]

def test_reject_traversal():
    with pytest.raises(ValueError):
        extract_pages("../secret.txt", b"hello")

def test_reject_oversized():
    with pytest.raises(ValueError):
        extract_pages("a.txt", b"x" * (5 * 1024 * 1024 + 1))

def test_blank_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    output = BytesIO()
    writer.write(output)
    assert extract_pages("blank.pdf", output.getvalue()) == []

def test_rrf_deduplicates():
    a = {"id": 1, "text": "A", "source": "a"}
    b = {"id": 2, "text": "B", "source": "b"}
    results = reciprocal_rank_fusion([[a, b], [b, a]])
    assert len(results) == 2
    assert {x["id"] for x in results} == {1, 2}
