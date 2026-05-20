"""Adapter for IBM docling.

docling exposes a DocumentConverter that returns a structured document; we
export to Markdown for parity with the other adapters and read table/image
counts directly from the document structure when available.
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import BaseAdapter, ParseOutput


class DoclingAdapter(BaseAdapter):
    name = "docling"

    def __init__(self) -> None:
        try:
            from docling.document_converter import DocumentConverter  # type: ignore

            self._cls = DocumentConverter
            self._available = True
        except Exception:
            self._cls = None
            self._available = False

    def is_available(self) -> bool:
        return self._available

    def supported_formats(self) -> set[str]:
        return {".pdf", ".docx", ".pptx", ".html", ".htm", ".md"}

    def parse(self, path: Path) -> ParseOutput:
        if not self._available:
            return ParseOutput(error="docling not installed")
        converter = self._cls()  # type: ignore[misc]
        result = converter.convert(str(path))
        doc = getattr(result, "document", None) or result
        md = doc.export_to_markdown() if hasattr(doc, "export_to_markdown") else str(doc)

        tables = getattr(doc, "tables", None)
        pictures = getattr(doc, "pictures", None)
        table_count = len(tables) if tables is not None else _count_md_tables(md)
        image_count = len(pictures) if pictures is not None else _count_md_images(md)

        return ParseOutput(
            text=md,
            raw_markdown=md,
            table_count=table_count,
            image_count=image_count,
        )


def _count_md_tables(md: str) -> int:
    return len(re.findall(r"^\s*\|?\s*:?-{3,}\s*(\|\s*:?-{3,}\s*)+\|?\s*$", md, re.MULTILINE))


def _count_md_images(md: str) -> int:
    return len(re.findall(r"!\[[^\]]*\]\([^)]+\)", md))
