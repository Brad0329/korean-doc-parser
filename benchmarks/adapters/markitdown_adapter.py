"""Adapter for Microsoft markitdown.

markitdown returns a single Markdown string and does not natively expose
table/image counts, so we infer table count from GFM pipe-table headers and
image count from `![...](...)` syntax.
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import BaseAdapter, ParseOutput


class MarkitdownAdapter(BaseAdapter):
    name = "markitdown"

    def __init__(self) -> None:
        try:
            from markitdown import MarkItDown  # type: ignore

            self._cls = MarkItDown
            self._available = True
        except Exception:
            self._cls = None
            self._available = False

    def is_available(self) -> bool:
        return self._available

    def supported_formats(self) -> set[str]:
        return {".pdf", ".docx", ".pptx", ".xlsx", ".html", ".htm", ".txt", ".csv"}

    def parse(self, path: Path) -> ParseOutput:
        if not self._available:
            return ParseOutput(error="markitdown not installed")
        md = self._cls()  # type: ignore[misc]
        result = md.convert(str(path))
        text = getattr(result, "text_content", "") or ""
        return ParseOutput(
            text=text,
            raw_markdown=text,
            table_count=_count_md_tables(text),
            image_count=_count_md_images(text),
        )


def _count_md_tables(md: str) -> int:
    """Count GFM pipe tables by their header-separator line: `|---|---|`."""
    return len(re.findall(r"^\s*\|?\s*:?-{3,}\s*(\|\s*:?-{3,}\s*)+\|?\s*$", md, re.MULTILINE))


def _count_md_images(md: str) -> int:
    return len(re.findall(r"!\[[^\]]*\]\([^)]+\)", md))
