"""Adapter for VikParuchuri/marker (marker-pdf on PyPI).

marker is PDF-focused; we report unsupported for non-PDF inputs.
The marker API has evolved; we try the modern PdfConverter path first and fall
back to the legacy `convert_single_pdf` if present.
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import BaseAdapter, ParseOutput


class MarkerAdapter(BaseAdapter):
    name = "marker"

    def __init__(self) -> None:
        self._mode: str | None = None
        self._modern = None
        self._legacy = None
        try:
            from marker.converters.pdf import PdfConverter  # type: ignore
            from marker.models import create_model_dict  # type: ignore

            self._modern = (PdfConverter, create_model_dict)
            self._mode = "modern"
            return
        except Exception:
            pass
        try:
            from marker.convert import convert_single_pdf  # type: ignore
            from marker.models import load_all_models  # type: ignore

            self._legacy = (convert_single_pdf, load_all_models)
            self._mode = "legacy"
        except Exception:
            self._mode = None

    def is_available(self) -> bool:
        return self._mode is not None

    def supported_formats(self) -> set[str]:
        return {".pdf"}

    def parse(self, path: Path) -> ParseOutput:
        if self._mode is None:
            return ParseOutput(error="marker not installed")
        if path.suffix.lower() != ".pdf":
            return ParseOutput(error=f"marker does not support {path.suffix}")

        if self._mode == "modern":
            PdfConverter, create_model_dict = self._modern  # type: ignore[misc]  # noqa: N806
            converter = PdfConverter(artifact_dict=create_model_dict())
            rendered = converter(str(path))
            text = getattr(rendered, "markdown", None) or str(rendered)
            images = getattr(rendered, "images", {}) or {}
            image_count = len(images) if hasattr(images, "__len__") else 0
        else:
            convert_single_pdf, load_all_models = self._legacy  # type: ignore[misc]
            models = load_all_models()
            text, images, _ = convert_single_pdf(str(path), models)
            image_count = len(images) if images else 0

        return ParseOutput(
            text=text,
            raw_markdown=text,
            table_count=_count_md_tables(text),
            image_count=image_count,
            extra={"mode": self._mode},
        )


def _count_md_tables(md: str) -> int:
    return len(re.findall(r"^\s*\|?\s*:?-{3,}\s*(\|\s*:?-{3,}\s*)+\|?\s*$", md, re.MULTILINE))
