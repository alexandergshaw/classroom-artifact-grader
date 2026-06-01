from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def extract_pdf(path: str | Path) -> str:
    reader = PdfReader(str(path))
    texts: list[str] = []
    for page in reader.pages:
        texts.append(page.extract_text() or "")
    return "\n".join(texts).strip()
