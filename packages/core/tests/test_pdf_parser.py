"""Tests for the pdfplumber-backed PDF parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from korean_doc_parser import ParseError, extract, get_parser
from korean_doc_parser.parsers.pdf import PdfParser
from tests._gt import load_ground_truth, verify_against_ground_truth

# ─────────────────────────────────────────────────────────────────────────────
# Registration + extension handling
# ─────────────────────────────────────────────────────────────────────────────


def test_pdf_parser_is_auto_registered() -> None:
    parser = get_parser(".pdf")
    assert parser is not None
    assert isinstance(parser, PdfParser)


def test_pdf_parser_supported_extensions() -> None:
    assert PdfParser().supported_extensions == (".pdf",)


def test_extract_uppercase_extension(pdf_simple: Path, tmp_path: Path) -> None:
    """Case-insensitive extension routing."""
    upper = tmp_path / "SAMPLE.PDF"
    upper.write_bytes(pdf_simple.read_bytes())
    result = extract(upper)
    assert result.metadata.format == "pdf"


# ─────────────────────────────────────────────────────────────────────────────
# Single-page synthetic PDF — ground-truth driven
# ─────────────────────────────────────────────────────────────────────────────


def test_pdf_simple_matches_ground_truth(pdf_simple: Path) -> None:
    result = extract(pdf_simple)
    gt = load_ground_truth(pdf_simple)
    assert gt is not None
    verify_against_ground_truth(result, gt)


def test_pdf_simple_extracts_title_and_author(pdf_simple: Path) -> None:
    result = extract(pdf_simple)
    assert result.metadata.title == "Synthetic PDF Title"
    assert result.metadata.author == "doc_parser tests"


# ─────────────────────────────────────────────────────────────────────────────
# Multi-page PDF — page_count + text aggregation
# ─────────────────────────────────────────────────────────────────────────────


def test_pdf_multipage_matches_ground_truth(pdf_multipage: Path) -> None:
    result = extract(pdf_multipage)
    gt = load_ground_truth(pdf_multipage)
    assert gt is not None
    verify_against_ground_truth(result, gt)


def test_pdf_multipage_page_count(pdf_multipage: Path) -> None:
    result = extract(pdf_multipage)
    assert result.metadata.page_count == 3


# ─────────────────────────────────────────────────────────────────────────────
# Table extraction — at least one table, well-formed rows
# ─────────────────────────────────────────────────────────────────────────────


def test_pdf_with_table_recognizes_table(pdf_with_table: Path) -> None:
    result = extract(pdf_with_table)
    assert len(result.tables) >= 1
    table = result.tables[0]
    assert table.page_no == 1

    flat = [cell for row in table.rows for cell in row]
    assert any("Item" in c for c in flat)
    assert any("Revenue" in c for c in flat)


def test_pdf_with_table_matches_ground_truth(pdf_with_table: Path) -> None:
    result = extract(pdf_with_table)
    gt = load_ground_truth(pdf_with_table)
    assert gt is not None
    verify_against_ground_truth(result, gt)


# ─────────────────────────────────────────────────────────────────────────────
# Error path — corrupt file raises ParseError (not a leaked low-level exception)
# ─────────────────────────────────────────────────────────────────────────────


def test_extract_raises_parse_error_on_corrupt_pdf(tmp_path: Path) -> None:
    bogus = tmp_path / "broken.pdf"
    bogus.write_bytes(b"not actually a PDF, just bytes")
    with pytest.raises(ParseError, match="Failed to parse PDF"):
        extract(bogus)


# ─────────────────────────────────────────────────────────────────────────────
# Image metadata extraction (bitmap bytes deferred to v0.2)
# ─────────────────────────────────────────────────────────────────────────────


def test_pdf_with_image_records_image_metadata(pdf_with_image: Path) -> None:
    result = extract(pdf_with_image)
    assert len(result.images) == 1
    img = result.images[0]
    assert img.page_no == 1
    assert img.bbox is not None
    assert img.width > 0
    assert img.height > 0
    # bitmap extraction deferred to v0.2 — placeholders documented
    assert img.file_path == ""
    assert img.sha256 == ""


def test_pdf_with_image_matches_ground_truth(pdf_with_image: Path) -> None:
    result = extract(pdf_with_image)
    gt = load_ground_truth(pdf_with_image)
    assert gt is not None
    verify_against_ground_truth(result, gt)


# ─────────────────────────────────────────────────────────────────────────────
# _to_str_or_none — defensive metadata coercion
# ─────────────────────────────────────────────────────────────────────────────


def test_to_str_or_none_returns_none_for_none() -> None:
    from korean_doc_parser.parsers.pdf import _to_str_or_none

    assert _to_str_or_none(None) is None


def test_to_str_or_none_decodes_utf8_bytes() -> None:
    from korean_doc_parser.parsers.pdf import _to_str_or_none

    assert _to_str_or_none("한글 제목".encode()) == "한글 제목"


def test_to_str_or_none_falls_back_to_latin1_for_invalid_utf8() -> None:
    from korean_doc_parser.parsers.pdf import _to_str_or_none

    result = _to_str_or_none(b"\xff\xfe")
    assert isinstance(result, str)
    assert len(result) == 2  # latin-1 maps byte-for-byte


def test_to_str_or_none_passes_str_through() -> None:
    from korean_doc_parser.parsers.pdf import _to_str_or_none

    assert _to_str_or_none("plain title") == "plain title"
