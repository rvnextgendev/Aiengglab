import pytest
pytest.importorskip('sqlalchemy')
pytest.importorskip('pgvector')
from app.persistent_rag import split_text

def test_empty_document():
    assert split_text("  ") == []

def test_short_document():
    assert split_text("Return policy is 14 days.") == ["Return policy is 14 days."]

def test_chunk_overlap():
    chunks = split_text("abcdefghij", chunk_size=6, overlap=2)
    assert chunks == ["abcdef", "efghij"]

def test_bad_chunk_config():
    import pytest
    with pytest.raises(ValueError):
        split_text("hello", chunk_size=3, overlap=3)
