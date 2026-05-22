"""Tests for the namespace-agnostic HWPX parser."""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

from korean_doc_parser import ParseError, extract, get_parser
from korean_doc_parser.parsers.hwpx import (
    HwpxParser,
    _local_name,
    _read_opf_title,
    _table_to_rows,
)
from tests._gt import load_ground_truth, verify_against_ground_truth

# ─────────────────────────────────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────────────────────────────────


def test_hwpx_parser_is_auto_registered() -> None:
    parser = get_parser(".hwpx")
    assert parser is not None
    assert isinstance(parser, HwpxParser)


def test_hwpx_parser_supported_extensions() -> None:
    assert HwpxParser().supported_extensions == (".hwpx",)


# ─────────────────────────────────────────────────────────────────────────────
# Simple HWPX — paragraphs + opf title
# ─────────────────────────────────────────────────────────────────────────────


def test_hwpx_simple_matches_ground_truth(hwpx_simple: Path) -> None:
    result = extract(hwpx_simple)
    gt = load_ground_truth(hwpx_simple)
    assert gt is not None
    verify_against_ground_truth(result, gt)


def test_hwpx_simple_extracts_title_from_opf(hwpx_simple: Path) -> None:
    result = extract(hwpx_simple)
    assert result.metadata.title == "HWPX 합성 픽스처"


def test_hwpx_simple_text_aggregation(hwpx_simple: Path) -> None:
    result = extract(hwpx_simple)
    assert "HWPX 합성 픽스처" in result.markdown
    assert "코드로 생성한 최소 HWPX" in result.markdown


# ─────────────────────────────────────────────────────────────────────────────
# Table extraction — nested <tbl> walked namespace-agnostically
# ─────────────────────────────────────────────────────────────────────────────


def test_hwpx_with_table_recognizes_table(hwpx_with_table: Path) -> None:
    result = extract(hwpx_with_table)
    assert len(result.tables) == 1
    table = result.tables[0]
    assert table.rows == [["A", "B"], ["1", "2"]]


def test_hwpx_with_table_text_excludes_table_cells(hwpx_with_table: Path) -> None:
    """Paragraphs containing tables should not also emit cell text into markdown."""
    result = extract(hwpx_with_table)
    # The heading paragraph still appears in markdown:
    assert "표 포함 HWPX" in result.markdown
    # But the table cells live only in result.tables, not duplicated in markdown:
    assert "A" not in result.markdown.split("표 포함 HWPX", 1)[1]


def test_hwpx_with_table_matches_ground_truth(hwpx_with_table: Path) -> None:
    result = extract(hwpx_with_table)
    gt = load_ground_truth(hwpx_with_table)
    assert gt is not None
    verify_against_ground_truth(result, gt)


# ─────────────────────────────────────────────────────────────────────────────
# Image extraction — BinData / Resources / PIL-failure fallback
# ─────────────────────────────────────────────────────────────────────────────


def test_hwpx_with_image_extracts_bitmap(hwpx_with_image: Path) -> None:
    """BinData/ PNG → tempfile written, sha256/dimensions/mime populated."""
    result = extract(hwpx_with_image)
    assert len(result.images) == 1
    img = result.images[0]
    assert img.file_path  # non-empty tempfile path
    assert Path(img.file_path).is_file()
    assert len(img.sha256) == 64  # sha256 hex digest
    assert img.size_bytes > 0
    assert img.width == 32 and img.height == 32
    assert img.mime_type == "image/png"
    assert img.file_path.endswith(".png")


def test_hwpx_with_image_matches_ground_truth(hwpx_with_image: Path) -> None:
    result = extract(hwpx_with_image)
    gt = load_ground_truth(hwpx_with_image)
    assert gt is not None
    verify_against_ground_truth(result, gt)


def test_hwpx_with_image_resources_extracts_jpeg(hwpx_with_image_resources: Path) -> None:
    """Contents/Resources/ JPEG → second media-root branch + JPEG format."""
    result = extract(hwpx_with_image_resources)
    assert len(result.images) == 1
    img = result.images[0]
    assert img.width == 48 and img.height == 24
    assert img.mime_type == "image/jpeg"
    assert img.file_path.endswith(".jpg")
    assert len(img.sha256) == 64


def test_hwpx_with_image_resources_matches_ground_truth(
    hwpx_with_image_resources: Path,
) -> None:
    result = extract(hwpx_with_image_resources)
    gt = load_ground_truth(hwpx_with_image_resources)
    assert gt is not None
    verify_against_ground_truth(result, gt)


def test_hwpx_with_image_corrupt_falls_back_to_octet_stream(
    hwpx_with_image_corrupt: Path,
) -> None:
    """PIL inspect failure must not raise — fallback to (0, 0, octet-stream)."""
    result = extract(hwpx_with_image_corrupt)
    assert len(result.images) == 1
    img = result.images[0]
    assert img.width == 0 and img.height == 0
    assert img.mime_type == "application/octet-stream"
    assert img.size_bytes > 0  # bytes still written to disk
    assert img.file_path.endswith(".bin")
    assert len(img.sha256) == 64  # sha256 computed regardless


def test_hwpx_with_image_corrupt_matches_ground_truth(
    hwpx_with_image_corrupt: Path,
) -> None:
    result = extract(hwpx_with_image_corrupt)
    gt = load_ground_truth(hwpx_with_image_corrupt)
    assert gt is not None
    verify_against_ground_truth(result, gt)


# ─────────────────────────────────────────────────────────────────────────────
# Error path — corrupt file
# ─────────────────────────────────────────────────────────────────────────────


def test_extract_raises_parse_error_on_corrupt_hwpx(tmp_path: Path) -> None:
    bogus = tmp_path / "broken.hwpx"
    bogus.write_bytes(b"not a zip")
    with pytest.raises(ParseError, match="Failed to parse HWPX"):
        extract(bogus)


# ─────────────────────────────────────────────────────────────────────────────
# Helper unit tests
# ─────────────────────────────────────────────────────────────────────────────


def test_local_name_strips_namespace() -> None:
    assert _local_name("{http://example.com}foo") == "foo"
    assert _local_name("bar") == "bar"


def test_table_to_rows_handles_empty_rows() -> None:
    xml = """<root xmlns="http://x">
      <tbl>
        <tr><tc><t>x</t></tc><tc><t>y</t></tc></tr>
        <tr></tr>
      </tbl>
    </root>"""
    root = ET.fromstring(xml)
    tbl = next(e for e in root.iter() if _local_name(e.tag) == "tbl")
    rows = _table_to_rows(tbl)
    assert rows == [["x", "y"]]  # empty <tr> dropped


def test_read_opf_title_returns_none_when_hpf_missing(tmp_path: Path) -> None:
    """If Contents/content.hpf is absent, title is ``None`` (no exception)."""
    p = tmp_path / "empty.hwpx"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("Contents/section0.xml", "<root/>")
    with zipfile.ZipFile(p) as zf:
        assert _read_opf_title(zf) is None


def test_read_opf_title_returns_none_on_invalid_xml(tmp_path: Path) -> None:
    p = tmp_path / "bad_hpf.hwpx"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("Contents/content.hpf", b"<<not xml>>")
    with zipfile.ZipFile(p) as zf:
        assert _read_opf_title(zf) is None
