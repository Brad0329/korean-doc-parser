"""Adapter for our own korean_doc_parser — v0.2.0 self-benchmark target.

Wraps :func:`korean_doc_parser.extract` so ``compare.py`` can measure the
shipped parser against the same fixture set the external libraries
(markitdown / docling / marker / unstructured) are scored on.

The HWP parser lives in the optional ``korean_doc_parser_hwp`` extras package;
we import it eagerly so ``.hwp`` routes correctly. If extras aren't installed
(core-only env) the import is best-effort skipped and ``.hwp`` falls out of
:meth:`supported_formats`.
"""

from __future__ import annotations

from pathlib import Path

from .base import BaseAdapter, ParseOutput


class KoreanDocParserAdapter(BaseAdapter):
    name = "korean_doc_parser"

    def __init__(self) -> None:
        try:
            import korean_doc_parser  # noqa: F401

            self._core_available = True
        except Exception:
            self._core_available = False

        try:
            import korean_doc_parser_hwp  # noqa: F401

            self._hwp_available = True
        except Exception:
            self._hwp_available = False

    def is_available(self) -> bool:
        return self._core_available

    def supported_formats(self) -> set[str]:
        if not self._core_available:
            return set()
        formats = {".pdf", ".docx", ".hwpx"}
        if self._hwp_available:
            formats.add(".hwp")
        return formats

    def parse(self, path: Path) -> ParseOutput:
        if not self._core_available:
            return ParseOutput(error="korean_doc_parser not installed")

        from korean_doc_parser import extract

        result = extract(path)
        return ParseOutput(
            text=result.markdown,
            table_count=len(result.tables),
            image_count=len(result.images),
            raw_markdown=result.markdown,
        )
