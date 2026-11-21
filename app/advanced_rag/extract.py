"""Bounded TXT/PDF extraction. PDF is text-based only; no OCR."""
from io import BytesIO
from pathlib import Path
from pypdf import PdfReader

MAX_BYTES = 5 * 1024 * 1024
MAX_PAGES = 100
MAX_CHARS = 250_000

def extract_pages(filename: str, data: bytes) -> list[tuple[int, str]]:
    name = Path(filename).name
    if name != filename or not name.lower().endswith((".pdf", ".txt")):
        raise ValueError("Only simple .pdf and .txt filenames are accepted")
    if not data or len(data) > MAX_BYTES:
        raise ValueError("File must be 1 byte to 5 MB")
    if name.lower().endswith(".txt"):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("TXT must be UTF-8") from exc
        if len(text) > MAX_CHARS:
            raise ValueError("Too much extracted text")
        return [(1, text)] if text.strip() else []
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise ValueError("Encrypted PDF not supported")
        if len(reader.pages) > MAX_PAGES:
            raise ValueError("PDF exceeds page limit")
        pages = []
        total = 0
        for index, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            total += len(text)
            if total > MAX_CHARS:
                raise ValueError("Too much extracted text")
            if text.strip():
                pages.append((index, text))
        return pages
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Unable to extract PDF text") from exc
