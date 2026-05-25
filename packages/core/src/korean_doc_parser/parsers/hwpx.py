"""HWPX parser — direct XML walk (Phase 0 decision: self-implement, MIT).

HWPX is a ZIP containing OPF metadata (``Contents/content.hpf``) and one or
more section XML files (``Contents/section*.xml``) using Hancom's hwpml
namespaces. Global libraries don't cover this format well, so we walk the
XML namespace-agnostically (via local-name) — tolerates both the rich schema
emitted by 한/글 and minimal synthetic fixtures.

Output:
* Markdown per ``<*:p>`` paragraph (text nodes ``<*:t>`` joined)
* Tables: one ``ParsedTable`` per ``<*:tbl>`` element
* Images: ``BinData/*`` and ``Contents/Resources/*`` extracted to tempfiles
* Metadata: ``opf:title`` from ``Contents/content.hpf``
"""

from __future__ import annotations

import hashlib
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO
from pathlib import Path

from korean_doc_parser.core import (
    BaseParser,
    ExtractedImage,
    ParsedTable,
    ParseMetadata,
    ParseResult,
    register_parser,
)
from korean_doc_parser.exceptions import ParseError

__all__ = ["HwpxParser"]


def _local_name(tag: str) -> str:
    """Strip the ``{namespace}`` prefix from an XML tag."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


class HwpxParser(BaseParser):
    """Parse ``.hwpx`` files by walking the section XML directly."""

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        return (".hwpx",)

    def parse(self, path: Path) -> ParseResult:
        try:
            with zipfile.ZipFile(path) as zf:
                markdown_parts: list[str] = []
                tables: list[ParsedTable] = []

                for section_no, sec_name in enumerate(_section_names(zf), start=1):
                    root = ET.fromstring(zf.read(sec_name))
                    self._walk_section(root, section_no, markdown_parts, tables)

                title = _read_opf_title(zf)
                images = _extract_images(zf)

                metadata = ParseMetadata(
                    format="hwpx",
                    file_path=path,
                    title=title,
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
            msg = f"Failed to parse HWPX {path}: {exc}"
            raise ParseError(msg) from exc

    @staticmethod
    def _walk_section(
        root: ET.Element,
        section_no: int,
        markdown: list[str],
        tables: list[ParsedTable],
    ) -> None:
        """Emit markdown text per ``<*:p>`` and ``ParsedTable`` per ``<*:tbl>``.

        Paragraphs containing tables contribute the table to ``tables`` and do
        not also emit their (table-internal) text to ``markdown`` — to avoid
        duplicating the table cells in two places.
        """
        table_order = 0
        for p_elem in root.iter():
            if _local_name(p_elem.tag) != "p":
                continue

            inner_tables = [child for child in p_elem.iter() if _local_name(child.tag) == "tbl"]
            if inner_tables:
                for tbl in inner_tables:
                    tables.append(
                        ParsedTable(
                            rows=_table_to_rows(tbl),
                            page_no=None,
                            order_in_page=table_order,
                        )
                    )
                    table_order += 1
                continue

            # Pure-text paragraph
            texts = [t.text for t in p_elem.iter() if _local_name(t.tag) == "t" and t.text]
            joined = "".join(texts).strip()
            if joined:
                markdown.append(joined)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers (module-level so they're easy to unit-test)
# ─────────────────────────────────────────────────────────────────────────────


def _section_names(zf: zipfile.ZipFile) -> list[str]:
    """Return section XML members sorted by name (section0, section1, ...)."""
    return sorted(
        n for n in zf.namelist() if "section" in _local_name(n).lower() and n.endswith(".xml")
    )


def _read_opf_title(zf: zipfile.ZipFile) -> str | None:
    """Extract ``<opf:title>`` from ``Contents/content.hpf`` if present."""
    try:
        data = zf.read("Contents/content.hpf")
    except KeyError:
        return None
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None
    for elem in root.iter():
        if _local_name(elem.tag) == "title" and elem.text:
            stripped = elem.text.strip()
            if stripped:
                return stripped
    return None


def _table_to_rows(tbl: ET.Element) -> list[list[str]]:
    """Convert an HWPX ``<tbl>`` element to a list-of-rows of cell text."""
    rows: list[list[str]] = []
    for tr in tbl.iter():
        if _local_name(tr.tag) != "tr":
            continue
        cells: list[str] = []
        for tc in tr.iter():
            if _local_name(tc.tag) != "tc":
                continue
            texts = [t.text for t in tc.iter() if _local_name(t.tag) == "t" and t.text]
            cells.append("".join(texts))
        if cells:
            rows.append(cells)
    return rows


def _extract_images(zf: zipfile.ZipFile) -> list[ExtractedImage]:
    """Extract ``BinData/*`` and ``Contents/Resources/*`` as ExtractedImage entries."""
    media = sorted(
        n
        for n in zf.namelist()
        if (n.startswith("BinData/") or n.startswith("Contents/Resources/")) and not n.endswith("/")
    )
    images: list[ExtractedImage] = []
    for idx, name in enumerate(media):
        data = zf.read(name)
        sha = hashlib.sha256(data).hexdigest()
        width, height, mime = _inspect_image(data)

        suffix = Path(name).suffix or ".bin"
        with tempfile.NamedTemporaryFile(
            prefix=f"kdp_hwpx_{idx}_",
            suffix=suffix,
            delete=False,
        ) as fh:
            fh.write(data)
        tmp_path_str = fh.name

        images.append(
            ExtractedImage(
                page_no=None,
                section_no=None,
                bbox=None,
                bbox_unit="none",
                order_in_page=idx,
                text_before="",
                text_after="",
                section_title=None,
                file_path=tmp_path_str,
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
    return images


def _inspect_image(data: bytes) -> tuple[int, int, str]:
    """Return ``(width, height, mime_type)`` for raw image bytes, or ``(0, 0, octet-stream)`` on failure."""
    from PIL import Image

    try:
        with Image.open(BytesIO(data)) as img:
            width, height = img.size
            mime = Image.MIME.get(img.format or "", "application/octet-stream")
            return width, height, mime
    except Exception:
        return 0, 0, "application/octet-stream"


# ─────────────────────────────────────────────────────────────────────────────
# Auto-register on import
# ─────────────────────────────────────────────────────────────────────────────

register_parser(HwpxParser())
