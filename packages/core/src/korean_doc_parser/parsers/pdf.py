"""PDF parser backed by pdfplumber (text/tables/bbox) + pypdf (bitmap bytes).

Outputs:
* Markdown built from per-page ``extract_text()`` joined by blank lines
* Tables via pdfplumber's default extraction heuristic
* Images — bbox + page index from pdfplumber, bitmap bytes / sha256 / true
  ``width``·``height``·``mime`` from pypdf's ``page.images`` decoder
* ``ParseMetadata`` from pdfplumber's ``pdf.metadata`` (Title / Author)

Bitmap pairing strategy (v0.2): per-page index. Both libraries iterate the
page's XObject resources in the same order in practice, so ``images[i]`` from
pdfplumber describes the same XObject as pypdf's ``page.images[i]``. If
counts disagree (defensive case — e.g. inline image only one lib sees), the
unpaired pdfplumber entry keeps ``file_path=""`` / ``sha256=""`` and the
extra pypdf entry is dropped — the parse still succeeds.

The parser registers itself with the global registry on import.
"""

from __future__ import annotations

import hashlib
import tempfile
from io import BytesIO
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
    import pypdf

__all__ = ["PdfParser"]


class PdfParser(BaseParser):
    """Parse ``.pdf`` files using pdfplumber + pypdf."""

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        return (".pdf",)

    def parse(self, path: Path) -> ParseResult:
        import pdfplumber
        import pypdf

        try:
            with pdfplumber.open(path) as pdf, pypdf.PdfReader(str(path)) as reader:
                markdown_parts: list[str] = []
                tables: list[ParsedTable] = []
                images: list[ExtractedImage] = []

                pypdf_pages = list(reader.pages)
                for page_idx, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    if text:
                        markdown_parts.append(text)
                    self._extract_tables(page, page_idx, tables)
                    pypdf_page = (
                        pypdf_pages[page_idx - 1] if page_idx - 1 < len(pypdf_pages) else None
                    )
                    self._extract_images(page, pypdf_page, page_idx, images)

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
    def _extract_images(
        page: pdfplumber.page.Page,
        pypdf_page: pypdf.PageObject | None,
        page_no: int,
        out: list[ExtractedImage],
    ) -> None:
        bitmaps = _collect_bitmaps(pypdf_page, page_no) if pypdf_page is not None else []
        img: dict[str, Any]
        for img_idx, img in enumerate(page.images):
            bbox = (
                float(img.get("x0", 0.0)),
                float(img.get("top", 0.0)),
                float(img.get("x1", 0.0)),
                float(img.get("bottom", 0.0)),
            )
            bitmap = bitmaps[img_idx] if img_idx < len(bitmaps) else None
            if bitmap is not None:
                file_path, sha, width, height, size_bytes, mime = bitmap
            else:
                file_path, sha, mime = "", "", str(img.get("name", "image/unknown"))
                width = int(img.get("width", 0))
                height = int(img.get("height", 0))
                size_bytes = 0
            out.append(
                ExtractedImage(
                    page_no=page_no,
                    section_no=None,
                    bbox=bbox,
                    bbox_unit="px" if bbox is not None else "none",
                    order_in_page=img_idx,
                    text_before="",
                    text_after="",
                    section_title=None,
                    file_path=file_path,
                    sha256=sha,
                    width=width,
                    height=height,
                    size_bytes=size_bytes,
                    mime_type=mime,
                    detected_caption=None,
                    caption_method=None,
                    caption_pattern_score=0.0,
                )
            )


_BitmapInfo = tuple[str, str, int, int, int, str]
"""``(file_path, sha256, width, height, size_bytes, mime_type)``."""


def _collect_bitmaps(pypdf_page: pypdf.PageObject, page_no: int) -> list[_BitmapInfo]:
    """Extract bitmap bytes for one page and persist each to a tempfile.

    One pathological image (unsupported filter, decoder crash) is logged via
    ``None`` and skipped — the rest of the page still yields bitmaps.
    """
    from PIL import Image

    results: list[_BitmapInfo] = []
    for img_idx, img in enumerate(pypdf_page.images):
        try:
            data = img.data
            sha = hashlib.sha256(data).hexdigest()
            pil = img.image
            if pil is not None:
                width, height = pil.size
                fmt = pil.format or ""
                mime = Image.MIME.get(fmt, "application/octet-stream")
                suffix = f".{fmt.lower()}" if fmt else ".bin"
            else:
                width, height = _inspect_size(data)
                mime = "application/octet-stream"
                suffix = ".bin"
            with tempfile.NamedTemporaryFile(
                prefix=f"kdp_pdf_p{page_no}_{img_idx}_",
                suffix=suffix,
                delete=False,
            ) as fh:
                fh.write(data)
            results.append((fh.name, sha, width, height, len(data), mime))
        except Exception:
            results.append(("", "", 0, 0, 0, "application/octet-stream"))
    return results


def _inspect_size(data: bytes) -> tuple[int, int]:
    """PIL-based ``(width, height)`` fallback for bytes pypdf couldn't decode."""
    from PIL import Image

    try:
        with Image.open(BytesIO(data)) as img:
            return img.size
    except Exception:
        return 0, 0


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
