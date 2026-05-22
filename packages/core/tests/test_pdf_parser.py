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
# Image bitmap extraction (v0.2 — pypdf-backed, real bytes)
# ─────────────────────────────────────────────────────────────────────────────


def test_pdf_with_image_records_image_metadata(pdf_with_image: Path) -> None:
    result = extract(pdf_with_image)
    assert len(result.images) == 1
    img = result.images[0]
    assert img.page_no == 1
    assert img.bbox is not None
    assert img.width == 32
    assert img.height == 32
    assert img.mime_type == "image/png"


def test_pdf_with_image_extracts_real_bitmap(pdf_with_image: Path) -> None:
    """v0.2 invariant — file_path / sha256 are filled, file exists, sha matches bytes."""
    import hashlib

    result = extract(pdf_with_image)
    img = result.images[0]
    assert img.file_path != ""
    file_path = Path(img.file_path)
    assert file_path.exists()
    bytes_on_disk = file_path.read_bytes()
    assert hashlib.sha256(bytes_on_disk).hexdigest() == img.sha256
    assert img.size_bytes == len(bytes_on_disk)


def test_pdf_with_image_matches_ground_truth(pdf_with_image: Path) -> None:
    result = extract(pdf_with_image)
    gt = load_ground_truth(pdf_with_image)
    assert gt is not None
    verify_against_ground_truth(result, gt)


def test_pdf_with_image_jpeg_extracts_jpeg_bitmap(pdf_with_image_jpeg: Path) -> None:
    """``/DCTDecode`` filter — pypdf returns JPEG bytes, PIL detects format."""
    import hashlib

    result = extract(pdf_with_image_jpeg)
    assert len(result.images) == 1
    img = result.images[0]
    assert img.width == 48
    assert img.height == 32
    assert img.mime_type == "image/jpeg"
    assert img.file_path != ""
    assert img.size_bytes > 0
    assert hashlib.sha256(Path(img.file_path).read_bytes()).hexdigest() == img.sha256


def test_pdf_with_image_jpeg_matches_ground_truth(pdf_with_image_jpeg: Path) -> None:
    result = extract(pdf_with_image_jpeg)
    gt = load_ground_truth(pdf_with_image_jpeg)
    assert gt is not None
    verify_against_ground_truth(result, gt)


def test_pdf_with_image_cmyk_extracts_cmyk_jpeg(pdf_with_image_cmyk: Path) -> None:
    """CMYK colorspace — PIL detects JPEG format, mime is image/jpeg, bitmap valid."""
    result = extract(pdf_with_image_cmyk)
    assert len(result.images) == 1
    img = result.images[0]
    assert img.width == 40
    assert img.height == 40
    assert img.mime_type == "image/jpeg"
    assert img.file_path != ""


def test_pdf_with_image_cmyk_matches_ground_truth(pdf_with_image_cmyk: Path) -> None:
    result = extract(pdf_with_image_cmyk)
    gt = load_ground_truth(pdf_with_image_cmyk)
    assert gt is not None
    verify_against_ground_truth(result, gt)


def test_pdf_with_multi_images_assigns_correct_page_nos(
    pdf_with_multi_images: Path,
) -> None:
    """Per-page index matching must preserve page assignment across pages."""
    result = extract(pdf_with_multi_images)
    assert len(result.images) == 2
    page_nos = sorted(img.page_no for img in result.images)
    assert page_nos == [1, 2]
    # Each image's bitmap is independent — different sha256.
    shas = {img.sha256 for img in result.images}
    assert len(shas) == 2
    for img in result.images:
        assert img.width == 24
        assert img.height == 24
        assert img.mime_type == "image/png"
        assert Path(img.file_path).exists()


def test_pdf_with_multi_images_matches_ground_truth(
    pdf_with_multi_images: Path,
) -> None:
    result = extract(pdf_with_multi_images)
    gt = load_ground_truth(pdf_with_multi_images)
    assert gt is not None
    verify_against_ground_truth(result, gt)


# ─────────────────────────────────────────────────────────────────────────────
# Bitmap defensive paths — count mismatch + decoder failure fallbacks
# ─────────────────────────────────────────────────────────────────────────────


def test_extract_images_falls_back_when_pypdf_page_missing(
    pdf_with_image: Path,
) -> None:
    """``pypdf_page=None`` keeps pdfplumber bbox but leaves bitmap placeholders.

    Mirrors the v0.2 contract: pypdf failure on one page must not corrupt
    the result — the parse still succeeds with bbox-only images.
    """
    import pdfplumber

    from korean_doc_parser.core import ExtractedImage
    from korean_doc_parser.parsers.pdf import PdfParser

    out: list[ExtractedImage] = []
    with pdfplumber.open(pdf_with_image) as pdf:
        PdfParser._extract_images(pdf.pages[0], None, page_no=1, out=out)
    assert len(out) == 1
    assert out[0].file_path == ""
    assert out[0].sha256 == ""
    assert out[0].size_bytes == 0
    # pdfplumber metadata still populated
    assert out[0].bbox is not None
    assert out[0].width > 0


def test_inspect_size_returns_zero_on_invalid_bytes() -> None:
    """PIL fallback when pypdf hands us bytes it couldn't decode itself."""
    from korean_doc_parser.parsers.pdf import _inspect_size

    assert _inspect_size(b"not an image, garbage bytes") == (0, 0)


def test_inspect_size_reads_valid_png_bytes() -> None:
    """Sanity check the happy path of the size inspector."""
    from io import BytesIO

    from PIL import Image

    from korean_doc_parser.parsers.pdf import _inspect_size

    buf = BytesIO()
    Image.new("RGB", (17, 23), (10, 20, 30)).save(buf, format="PNG")
    assert _inspect_size(buf.getvalue()) == (17, 23)


def test_collect_bitmaps_handles_decoder_exception() -> None:
    """A single faulty image entry yields an empty placeholder; siblings survive."""
    from korean_doc_parser.parsers.pdf import _collect_bitmaps

    class _Boom:
        @property
        def data(self) -> bytes:
            raise RuntimeError("simulated pypdf decoder failure")

        @property
        def image(self) -> None:
            return None

    class _FakePage:
        def __init__(self) -> None:
            self.images = [_Boom()]

    results = _collect_bitmaps(_FakePage(), page_no=99)  # type: ignore[arg-type]
    assert results == [("", "", 0, 0, 0, "application/octet-stream")]


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
