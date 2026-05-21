"""PDF parser backed by pdfplumber (Phase 0 decision: self-implement).

Outputs text + tables + image metadata. Bitmap extraction (filling
``ExtractedImage.file_path`` / ``sha256`` with real bytes) is deferred to
v0.2 — see CHANGELOG. For v0.1 the image entries carry positional metadata
(bbox, width, height) but the file_path / sha256 are placeholders.

The parser registers itself with the global registry on import.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from korean_doc_parser.core import (
    BaseParser,
    ExtractedImage,
    ParsedTable,
    ParseMetadata,
    ParseResult,
    register_parser,
)
from korean_doc_parser.exceptions import ParseError

if TYPE_CHECKING:
    import pdfplumber.page

__all__ = ["PdfParser"]


class PdfParser(BaseParser):
    """Parse ``.pdf`` files using pdfplumber.

    Tables are extracted with pdfplumber's default heuristic. Images yield
    ``ExtractedImage`` entries with bbox + dimensions but no bitmap bytes;
    see module docstring.
    """

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        return (".pdf",)

    def parse(self, path: Path) -> ParseResult:
        import pdfplumber

        try:
            with pdfplumber.open(path) as pdf:
                markdown_parts: list[str] = []
                tables: list[ParsedTable] = []
                images: list[ExtractedImage] = []

                for page_idx, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    if text:
                        markdown_parts.append(text)
                    self._extract_tables(page, page_idx, tables)
                    self._extract_image_metadata(page, page_idx, images)

                pdf_meta: dict[str, Any] = pdf.metadata or {}
                metadata = ParseMetadata(
                    format="pdf",
                    file_path=path,
                    page_count=len(pdf.pages),
                    title=_to_str_or_none(pdf_meta.get("Title")),
                    author=_to_str_or_none(pdf_meta.get("Author")),
                )

                return ParseResult(
                    markdown="\n\n".join(markdown_parts),
                    metadata=metadata,
                    tables=tables,
                    images=images,
                )
        except ParseError:
            raise
        except Exception as exc:
            msg = f"Failed to parse PDF {path}: {exc}"
            raise ParseError(msg) from exc

    # ─────────────────────────────────────────────────────────────────────
    # Per-page helpers
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_tables(
        page: pdfplumber.page.Page,
        page_no: int,
        out: list[ParsedTable],
    ) -> None:
        raw_tables = page.extract_tables() or []
        for table_idx, raw_table in enumerate(raw_tables):
            cleaned_rows = [[cell or "" for cell in row] for row in raw_table]
            out.append(
                ParsedTable(
                    rows=cleaned_rows,
                    page_no=page_no,
                    order_in_page=table_idx,
                )
            )

    @staticmethod
    def _extract_image_metadata(
        page: pdfplumber.page.Page,
        page_no: int,
        out: list[ExtractedImage],
    ) -> None:
        img: dict[str, Any]
        for img_idx, img in enumerate(page.images):
            bbox = (
                float(img.get("x0", 0.0)),
                float(img.get("top", 0.0)),
                float(img.get("x1", 0.0)),
                float(img.get("bottom", 0.0)),
            )
            out.append(
                ExtractedImage(
                    page_no=page_no,
                    section_no=None,
                    bbox=bbox,
                    order_in_page=img_idx,
                    text_before="",
                    text_after="",
                    section_title=None,
                    file_path="",  # bitmap extraction deferred to v0.2
                    sha256="",
                    width=int(img.get("width", 0)),
                    height=int(img.get("height", 0)),
                    size_bytes=0,
                    mime_type=str(img.get("name", "image/unknown")),
                    detected_caption=None,
                    caption_method=None,
                    caption_pattern_score=0.0,
                )
            )


def _to_str_or_none(value: object) -> str | None:
    """Coerce PDF metadata values (bytes / PdfObject / str / None) to ``str | None``.

    pdfplumber returns ``str``-like objects for most fields, but some PDFs
    encode metadata as bytes; we normalize defensively.
    """
    if value is None:
        return None
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.decode("latin-1", errors="replace")
    return str(value)


# ─────────────────────────────────────────────────────────────────────────────
# Auto-register on import
# ─────────────────────────────────────────────────────────────────────────────

register_parser(PdfParser())
