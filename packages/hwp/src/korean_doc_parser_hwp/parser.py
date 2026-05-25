"""HWP (legacy binary 5.x) parser backed by pyhwp + BeautifulSoup.

Pipeline (ported from ``lets_portal/backend/utils/file_parser.py``,
``_parse_hwp_pyhwp`` + ``_xhtml_to_markdown``, commit history pre-2026-05-21,
adapted to korean-doc-parser's ``BaseParser`` / ``ParseResult`` shape):

1. ``hwp5.xmlmodel.Hwp5File`` opens the OLE compound document.
2. ``hwp5.hwp5html.HTMLTransform.transform_hwp5_to_dir`` writes
   ``index.xhtml`` + ``styles.css`` + ``bindata/`` into a tempdir.
3. BeautifulSoup walks ``<p>`` and ``<table>`` from ``<body>``, building
   markdown for paragraphs and a separate ``ParsedTable`` list for tables.
4. (v0.4.5, worklog/017) ``bindata/`` files are copied to persistent tempfiles
   and surfaced as :class:`ExtractedImage` — bbox / page_no are ``None``
   because HWP's coordinate model doesn't map to the PDF-style bbox.

Why two outputs (markdown + tables): callers downstream of this parser want
tables as structured rows for tabular RAG, not as flattened markdown lines.
This matches the contract of the PDF / DOCX / HWPX parsers.

License: this module ships in ``packages/hwp/`` because ``hwp5`` (pyhwp)
is AGPL-3.0-or-later. The core package is unaffected.
"""

from __future__ import annotations

import hashlib
import mimetypes
import tempfile
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

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
    from bs4 import Tag

__all__ = ["HwpParser"]


class HwpParser(BaseParser):
    """Parse ``.hwp`` files via pyhwp's XHTML transform.

    v0.4.5 contract:
    * ``markdown`` — XHTML paragraphs joined with double newlines
    * ``tables`` — ``ParsedTable`` with ``page_no=None`` (HWP's logical
      pagination doesn't map cleanly to XHTML)
    * ``images`` — every file in pyhwp's ``bindata/`` output, copied to
      persistent tempfiles. ``page_no`` / ``bbox`` are ``None`` (worklog/017
      § 2-3): HWP's per-page positioning doesn't map to the PDF-style bbox
      and the XHTML emitted by pyhwp doesn't carry per-paragraph image
      anchors. ``order_in_page`` is the bindata sort order, which matches
      pyhwp's BinData stream numbering.
    """

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        return (".hwp",)

    def parse(self, path: Path) -> ParseResult:
        from hwp5.hwp5html import HTMLTransform
        from hwp5.xmlmodel import Hwp5File

        try:
            transform = HTMLTransform()
            hwp5file = Hwp5File(str(path))
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    transform.transform_hwp5_to_dir(hwp5file, tmpdir)
                    html_path = Path(tmpdir) / "index.xhtml"
                    if not html_path.exists():
                        msg = f"pyhwp produced no index.xhtml for {path}"
                        raise ParseError(msg)
                    html = html_path.read_text(encoding="utf-8")
                    # bindata/ lives inside tmpdir and disappears with the
                    # TemporaryDirectory — copy each blob out before the
                    # context manager exits.
                    images = _collect_bindata_images(Path(tmpdir) / "bindata")
            finally:
                hwp5file.close()

            markdown, tables = _xhtml_to_markdown_and_tables(html)
            metadata = ParseMetadata(format="hwp", file_path=path)

            return ParseResult(
                markdown=markdown,
                metadata=metadata,
                tables=tables,
                images=images,
            )
        except ParseError:
            raise
        except Exception as exc:
            msg = f"Failed to parse HWP {path}: {exc}"
            raise ParseError(msg) from exc


# ─────────────────────────────────────────────────────────────────────────────
# XHTML → (markdown, tables) — adapted from lets_portal _xhtml_to_markdown
# ─────────────────────────────────────────────────────────────────────────────


def _xhtml_to_markdown_and_tables(html: str) -> tuple[str, list[ParsedTable]]:
    """Walk pyhwp's XHTML output and split into markdown paragraphs + tables.

    Tables are returned as :class:`ParsedTable` (no ``page_no`` — HWP's logical
    pagination doesn't map cleanly to XHTML output). Nested tables are flattened
    into their parent cell's text rather than emitted as separate rows.
    """
    from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

    soup = BeautifulSoup(html, "lxml")
    body = soup.find("body")
    if body is None:
        return "", []

    parts: list[str] = []
    tables: list[ParsedTable] = []
    processed: set[int] = set()

    table_idx = 0
    for elem in body.find_all(["p", "table"]):
        if any(id(ancestor) in processed for ancestor in elem.parents):
            continue

        if elem.name == "table":
            rows = _html_table_rows(elem)
            if rows:
                tables.append(
                    ParsedTable(
                        rows=rows,
                        page_no=None,
                        order_in_page=table_idx,
                    )
                )
                table_idx += 1
            processed.add(id(elem))
            for descendant in elem.descendants:
                if hasattr(descendant, "name"):
                    processed.add(id(descendant))
        elif elem.name == "p":
            text = elem.get_text(separator=" ", strip=True)
            if text:
                parts.append(text)

    return "\n\n".join(parts), tables


def _html_table_rows(table_elem: Tag) -> list[list[str]]:
    """Flatten a BeautifulSoup ``<table>`` into rows of cell strings.

    Nested tables are absorbed into the parent cell's text (their structure is
    lost — preserving it would require recursive table_no assignment and is
    not in the v0.2 contract).
    """
    rows: list[list[str]] = []
    for tr in table_elem.find_all("tr", recursive=True):
        closest_table = tr.find_parent("table")
        if closest_table is not table_elem:
            continue

        cells: list[str] = []
        for cell in tr.find_all(["td", "th"], recursive=False):
            text = cell.get_text(separator=" ", strip=True)
            cells.append(text)
        if cells:
            rows.append(cells)

    if not rows:
        return []

    max_cols = max(len(row) for row in rows)
    return [row + [""] * (max_cols - len(row)) for row in rows]


# ─────────────────────────────────────────────────────────────────────────────
# bindata/ → ExtractedImage (v0.4.5, worklog/017)
# ─────────────────────────────────────────────────────────────────────────────


def _collect_bindata_images(bindata_dir: Path) -> list[ExtractedImage]:
    """Copy each ``bindata/`` file to a persistent tempfile + materialise as
    :class:`ExtractedImage`. Returns ``[]`` if the directory is missing.

    pyhwp names BinData streams ``BIN0001.{png,jpg,bmp,...}`` etc. We sort by
    filename to keep ``order_in_page`` deterministic across runs — the actual
    stream-to-anchor mapping is lost in pyhwp's XHTML output, which is the
    real reason we leave ``page_no`` / ``bbox`` as ``None`` (worklog/007 § 2-3).
    """
    if not bindata_dir.is_dir():
        return []
    files = sorted(p for p in bindata_dir.iterdir() if p.is_file())
    out: list[ExtractedImage] = []
    for order, src in enumerate(files, start=1):
        try:
            data = src.read_bytes()
        except OSError:
            continue
        if not data:
            continue
        sha = hashlib.sha256(data).hexdigest()
        suffix = src.suffix or ".bin"
        with tempfile.NamedTemporaryFile(
            prefix=f"kdp_hwp_{order:04d}_",
            suffix=suffix,
            delete=False,
        ) as fh:
            fh.write(data)
            file_path = fh.name
        width, height = _safe_image_size(data)
        mime = mimetypes.guess_type(src.name)[0] or "application/octet-stream"
        out.append(
            ExtractedImage(
                page_no=None,
                section_no=None,
                bbox=None,
                order_in_page=order,
                text_before="",
                text_after="",
                section_title=None,
                file_path=file_path,
                sha256=sha,
                width=width,
                height=height,
                size_bytes=len(data),
                mime_type=mime,
                detected_caption=None,
                caption_method=None,
                caption_pattern_score=0.0,
            )
        )
    return out


def _safe_image_size(data: bytes) -> tuple[int, int]:
    """PIL-based ``(width, height)``; ``(0, 0)`` if PIL can't decode.

    Same pattern as ``parsers/pptx._safe_image_size`` — kept duplicated here
    because the hwp package can't import from pptx (cross-package), and core
    doesn't yet host a shared image-utils module (v0.5+ refactor candidate).
    """
    from io import BytesIO

    from PIL import Image

    try:
        with Image.open(BytesIO(data)) as img:
            return int(img.width), int(img.height)
    except Exception:
        return 0, 0


# ─────────────────────────────────────────────────────────────────────────────
# Auto-register on import
# ─────────────────────────────────────────────────────────────────────────────

register_parser(HwpParser())
