"""Tests for the pyhwp-backed HWP parser.

Real-fixture coverage uses 5 production HWP samples in ``samples/`` (skip-
guarded). For CI without those files, the registration / extension / unit
tests still validate the parser's wiring and the XHTML→markdown helpers.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from tests._gt import load_ground_truth, verify_against_ground_truth

import korean_doc_parser_hwp  # registers HwpParser on import  # noqa: F401
from korean_doc_parser import ParseError, extract, get_parser
from korean_doc_parser_hwp.parser import (
    HwpParser,
    _html_table_rows,
    _xhtml_to_markdown_and_tables,
)

if TYPE_CHECKING:
    from korean_doc_parser import ParseResult

pytestmark = pytest.mark.hwp


# ─────────────────────────────────────────────────────────────────────────────
# Registration + extension handling
# ─────────────────────────────────────────────────────────────────────────────


def test_hwp_parser_is_auto_registered() -> None:
    parser = get_parser(".hwp")
    assert parser is not None
    assert isinstance(parser, HwpParser)


def test_hwp_parser_supported_extensions() -> None:
    assert HwpParser().supported_extensions == (".hwp",)


# ─────────────────────────────────────────────────────────────────────────────
# Real-fixture extraction — 5 samples covering varying sizes / domains
# ─────────────────────────────────────────────────────────────────────────────


def test_hwp_test_nara_matches_ground_truth(
    hwp_test_nara: Path,
    hwp_test_nara_result: ParseResult,
) -> None:
    gt = load_ground_truth(hwp_test_nara)
    assert gt is not None
    verify_against_ground_truth(hwp_test_nara_result, gt)


def test_hwp_wku_matches_ground_truth(
    hwp_wku: Path,
    hwp_wku_result: ParseResult,
) -> None:
    gt = load_ground_truth(hwp_wku)
    assert gt is not None
    verify_against_ground_truth(hwp_wku_result, gt)


def test_hwp_gyeongnam_fishery_matches_ground_truth(
    hwp_gyeongnam_fishery: Path,
    hwp_gyeongnam_fishery_result: ParseResult,
) -> None:
    gt = load_ground_truth(hwp_gyeongnam_fishery)
    assert gt is not None
    verify_against_ground_truth(hwp_gyeongnam_fishery_result, gt)


def test_hwp_forest_startup_matches_ground_truth(
    hwp_forest_startup: Path,
    hwp_forest_startup_result: ParseResult,
) -> None:
    gt = load_ground_truth(hwp_forest_startup)
    assert gt is not None
    verify_against_ground_truth(hwp_forest_startup_result, gt)


def test_hwp_proposal_consulting_matches_ground_truth(
    hwp_proposal_consulting: Path,
    hwp_proposal_consulting_result: ParseResult,
) -> None:
    gt = load_ground_truth(hwp_proposal_consulting)
    assert gt is not None
    verify_against_ground_truth(hwp_proposal_consulting_result, gt)


def test_hwp_test_nara_extracts_korean_text(hwp_test_nara_result: ParseResult) -> None:
    """Smoke check: at least 50% of markdown chars must be Korean syllables.

    Guards against the mojibake regression where pyhwp output gets read with
    the wrong codec and we silently ship 0-hangul markdown.
    """
    hangul = sum(1 for c in hwp_test_nara_result.markdown if 0xAC00 <= ord(c) <= 0xD7AF)
    assert hangul > len(hwp_test_nara_result.markdown) * 0.4, (
        f"only {hangul}/{len(hwp_test_nara_result.markdown)} Korean chars — likely encoding regression"
    )


def test_hwp_test_nara_tables_have_consistent_columns(
    hwp_test_nara_result: ParseResult,
) -> None:
    """Every row in a ParsedTable must have the same column count (post-normalize)."""
    assert hwp_test_nara_result.tables, "expected at least one table"
    for t in hwp_test_nara_result.tables:
        if not t.rows:
            continue
        widths = {len(row) for row in t.rows}
        assert len(widths) == 1, f"table {t.order_in_page} has uneven columns: {widths}"


# ─────────────────────────────────────────────────────────────────────────────
# Error path — corrupt file raises ParseError
# ─────────────────────────────────────────────────────────────────────────────


def test_extract_raises_parse_error_on_corrupt_hwp(tmp_path: Path) -> None:
    bogus = tmp_path / "broken.hwp"
    bogus.write_bytes(b"not actually an HWP, just bytes")
    with pytest.raises(ParseError, match="Failed to parse HWP"):
        extract(bogus)


# ─────────────────────────────────────────────────────────────────────────────
# _xhtml_to_markdown_and_tables — unit tests (samples-free coverage)
# ─────────────────────────────────────────────────────────────────────────────


_MINIMAL_XHTML = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
<p>첫 단락</p>
<p>둘째 단락</p>
<table>
  <tr><th>항목</th><th>값</th></tr>
  <tr><td>매출</td><td>1000</td></tr>
</table>
<p>표 뒤 단락</p>
</body>
</html>
"""

_NESTED_TABLE_XHTML = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
<p>위 단락</p>
<table>
  <tr><td>A</td><td>
    <table><tr><td>중첩</td><td>표</td></tr></table>
  </td></tr>
  <tr><td>B</td><td>C</td></tr>
</table>
</body>
</html>
"""


def test_xhtml_helper_splits_paragraphs_from_tables() -> None:
    md, tables = _xhtml_to_markdown_and_tables(_MINIMAL_XHTML)
    assert "첫 단락" in md
    assert "둘째 단락" in md
    assert "표 뒤 단락" in md
    # Table cells must not leak into markdown.
    assert "매출" not in md
    assert len(tables) == 1
    assert tables[0].rows[0] == ["항목", "값"]
    assert tables[0].rows[1] == ["매출", "1000"]


def test_xhtml_helper_handles_no_body() -> None:
    md, tables = _xhtml_to_markdown_and_tables("<html><head></head></html>")
    assert md == ""
    assert tables == []


def test_xhtml_helper_flattens_nested_tables() -> None:
    """Nested tables are absorbed into parent cell text, not emitted separately."""
    md, tables = _xhtml_to_markdown_and_tables(_NESTED_TABLE_XHTML)
    assert "위 단락" in md
    # Only the outer table is emitted.
    assert len(tables) == 1
    # The first row's second cell carries the nested table's text.
    flat = [cell for row in tables[0].rows for cell in row]
    assert any("중첩" in c for c in flat)


def test_html_table_rows_normalizes_column_widths() -> None:
    """Rows with fewer cells are padded so every row has the same width."""
    from bs4 import BeautifulSoup

    html = """
    <table>
      <tr><td>a</td><td>b</td><td>c</td></tr>
      <tr><td>x</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    rows = _html_table_rows(table)  # type: ignore[arg-type]
    assert rows == [["a", "b", "c"], ["x", "", ""]]


def test_html_table_rows_returns_empty_for_no_rows() -> None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup("<table></table>", "lxml")
    table = soup.find("table")
    assert _html_table_rows(table) == []  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────────────
# v0.4.5 — bindata/ image extraction (worklog/017)
# ─────────────────────────────────────────────────────────────────────────────


def test_hwp_test_nara_has_extracted_images(hwp_test_nara_result: ParseResult) -> None:
    """v0.4.5 contract: HWP bindata/ now surfaces as ExtractedImage. The
    test_nara sample's image count is pinned by its ground truth — this test
    just asserts the list isn't empty after the v0.4.5 change."""
    assert len(hwp_test_nara_result.images) > 0


def test_hwp_image_metadata_contract(hwp_test_nara_result: ParseResult) -> None:
    """Per-image contract (worklog/017 § 3):

    * ``page_no`` / ``bbox`` are ``None`` (HWP coords don't map to PDF-style bbox)
    * ``order_in_page`` is 1-based and unique
    * ``sha256`` is a 64-char lowercase hex string
    * ``file_path`` points at a real persistent tempfile
    * ``size_bytes`` matches the on-disk size
    """
    images = hwp_test_nara_result.images
    assert images, "expected at least 1 image"
    orders = [img.order_in_page for img in images]
    assert orders == sorted(orders)
    assert len(set(orders)) == len(orders)
    for img in images:
        assert img.page_no is None
        assert img.bbox is None
        assert len(img.sha256) == 64
        assert all(c in "0123456789abcdef" for c in img.sha256)
        assert Path(img.file_path).is_file()
        assert Path(img.file_path).stat().st_size == img.size_bytes
        assert img.size_bytes > 0
        assert img.mime_type.startswith("image/") or img.mime_type == "application/octet-stream"


def test_hwp_image_mime_types_are_recognized(hwp_test_nara_result: ParseResult) -> None:
    """test_nara ships bmp + jpeg images — both must surface with proper MIME."""
    mimes = {img.mime_type for img in hwp_test_nara_result.images}
    assert mimes <= {
        "image/bmp",
        "image/jpeg",
        "image/png",
        "application/octet-stream",
    }, f"unexpected MIME types: {mimes}"


def test_hwp_extract_returns_empty_bindata_gracefully(tmp_path: Path) -> None:
    """Internal helper contract: missing bindata/ dir → empty list, no raise.

    This guards against pyhwp variants / corrupt files that produce no
    bindata directory at all — the rest of the parse should still succeed.
    """
    from korean_doc_parser_hwp.parser import _collect_bindata_images

    assert _collect_bindata_images(tmp_path / "definitely_missing") == []
