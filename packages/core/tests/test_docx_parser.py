"""Tests for the python-docx-backed DOCX parser."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from korean_doc_parser import ParseError, extract, get_parser
from korean_doc_parser.parsers.docx import DocxParser
from tests._gt import load_ground_truth, verify_against_ground_truth

# ─────────────────────────────────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────────────────────────────────


def test_docx_parser_is_auto_registered() -> None:
    parser = get_parser(".docx")
    assert parser is not None
    assert isinstance(parser, DocxParser)


def test_docx_parser_supported_extensions() -> None:
    assert DocxParser().supported_extensions == (".docx",)


# ─────────────────────────────────────────────────────────────────────────────
# Simple DOCX — heading + paragraph
# ─────────────────────────────────────────────────────────────────────────────


def test_docx_simple_matches_ground_truth(docx_simple: Path) -> None:
    result = extract(docx_simple)
    gt = load_ground_truth(docx_simple)
    assert gt is not None
    verify_against_ground_truth(result, gt)


def test_docx_simple_promotes_heading_to_markdown(docx_simple: Path) -> None:
    """``Heading 1`` style paragraphs become ``# `` Markdown headings."""
    result = extract(docx_simple)
    assert result.markdown.startswith("# 테스트 문서 제목")


def test_docx_simple_metadata_format_and_path(docx_simple: Path) -> None:
    result = extract(docx_simple)
    assert result.metadata.format == "docx"
    assert result.metadata.file_path == docx_simple


# ─────────────────────────────────────────────────────────────────────────────
# Table extraction — single 3-by-3 table
# ─────────────────────────────────────────────────────────────────────────────


def test_docx_with_table_recognizes_table(docx_with_table: Path) -> None:
    result = extract(docx_with_table)
    assert len(result.tables) == 1
    table = result.tables[0]
    assert table.page_no is None  # DOCX has no native page concept
    assert table.rows[0] == ["항목", "값", "비고"]
    assert table.rows[1][0] == "매출"
    assert table.rows[2][1] == "600"


def test_docx_with_table_matches_ground_truth(docx_with_table: Path) -> None:
    result = extract(docx_with_table)
    gt = load_ground_truth(docx_with_table)
    assert gt is not None
    verify_against_ground_truth(result, gt)


# ─────────────────────────────────────────────────────────────────────────────
# Image extraction — bytes are written to a tempfile, sha256 matches
# ─────────────────────────────────────────────────────────────────────────────


def test_docx_with_image_extracts_one_image(docx_with_image: Path) -> None:
    result = extract(docx_with_image)
    assert len(result.images) == 1
    img = result.images[0]

    assert img.file_path != ""
    assert Path(img.file_path).is_file()
    assert img.sha256 != ""
    assert img.width > 0
    assert img.height > 0
    assert img.size_bytes > 0
    assert img.mime_type.startswith("image/")

    # Hash should match the bytes actually written to file_path
    written = Path(img.file_path).read_bytes()
    assert hashlib.sha256(written).hexdigest() == img.sha256


def test_docx_with_image_matches_ground_truth(docx_with_image: Path) -> None:
    result = extract(docx_with_image)
    gt = load_ground_truth(docx_with_image)
    assert gt is not None
    verify_against_ground_truth(result, gt)


# ─────────────────────────────────────────────────────────────────────────────
# Error path — corrupt file raises ParseError
# ─────────────────────────────────────────────────────────────────────────────


def test_extract_raises_parse_error_on_corrupt_docx(tmp_path: Path) -> None:
    bogus = tmp_path / "broken.docx"
    bogus.write_bytes(b"not really a docx")
    with pytest.raises(ParseError, match="Failed to parse DOCX"):
        extract(bogus)


# ─────────────────────────────────────────────────────────────────────────────
# _inspect_image — defensive fallback on malformed bytes
# ─────────────────────────────────────────────────────────────────────────────


def test_inspect_image_falls_back_on_garbage() -> None:
    from korean_doc_parser.parsers.docx import _inspect_image

    width, height, mime = _inspect_image(b"definitely not an image")
    assert (width, height, mime) == (0, 0, "application/octet-stream")


def test_inspect_image_reads_png_dimensions() -> None:
    from io import BytesIO

    from PIL import Image

    from korean_doc_parser.parsers.docx import _inspect_image

    buf = BytesIO()
    Image.new("RGB", (24, 16), (0, 0, 255)).save(buf, format="PNG")

    width, height, mime = _inspect_image(buf.getvalue())
    assert (width, height) == (24, 16)
    assert mime == "image/png"
