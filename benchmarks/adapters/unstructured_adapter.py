"""Adapter for Unstructured (unstructured-io/unstructured).

`partition` autodetects file type and returns a list of Element objects whose
categories include Table, Image, NarrativeText, etc. We use those categories
directly for table_count / image_count instead of inferring from Markdown.
"""

from __future__ import annotations

from pathlib import Path

from .base import BaseAdapter, ParseOutput


class UnstructuredAdapter(BaseAdapter):
    name = "unstructured"

    def __init__(self) -> None:
        try:
            from unstructured.partition.auto import partition  # type: ignore

            self._partition = partition
            self._available = True
        except Exception:
            self._partition = None
            self._available = False

    def is_available(self) -> bool:
        return self._available

    def supported_formats(self) -> set[str]:
        return {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".html", ".htm", ".txt", ".md"}

    def parse(self, path: Path) -> ParseOutput:
        if not self._available:
            return ParseOutput(error="unstructured not installed")
        elements = self._partition(filename=str(path))  # type: ignore[misc]

        parts: list[str] = []
        table_count = 0
        image_count = 0
        for el in elements:
            category = getattr(el, "category", "") or el.__class__.__name__
            if category == "Table":
                table_count += 1
                html = getattr(getattr(el, "metadata", None), "text_as_html", None)
                parts.append(html or str(el))
            elif category == "Image":
                image_count += 1
            else:
                parts.append(str(el))

        text = "\n\n".join(parts)
        return ParseOutput(
            text=text,
            table_count=table_count,
            image_count=image_count,
        )
