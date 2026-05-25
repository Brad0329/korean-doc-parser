"""Smoke tests for the synthetic fixture + ground-truth infrastructure.

Per-parser tests (Task #8 onwards) will exercise real parsing against these
fixtures. Here we verify that the infrastructure itself works:

* synthetic generators produce non-empty files
* ground-truth JSON is written alongside and parses
* :func:`verify_against_ground_truth` accepts a matching :class:`ParseResult`
  and rejects a mismatching one
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from korean_doc_parser import ParseMetadata, ParseResult
from tests._gt import GroundTruth, load_ground_truth, verify_against_ground_truth

# ─────────────────────────────────────────────────────────────────────────────
# Synthetic generators produce well-formed files + ground truth
# ─────────────────────────────────────────────────────────────────────────────


def test_docx_simple_is_a_zip(docx_simple: Path) -> None:
    assert docx_simple.is_file()
    assert docx_simple.stat().st_size > 0
    assert zipfile.is_zipfile(docx_simple)


def test_docx_with_table_is_a_zip(docx_with_table: Path) -> None:
    assert docx_with_table.is_file()
    assert zipfile.is_zipfile(docx_with_table)


def test_hwpx_simple_is_a_zip(hwpx_simple: Path) -> None:
    assert hwpx_simple.is_file()
    assert zipfile.is_zipfile(hwpx_simple)
    with zipfile.ZipFile(hwpx_simple) as zf:
        names = set(zf.namelist())
    assert {"mimetype", "Contents/content.hpf", "Contents/section0.xml"} <= names


@pytest.mark.parametrize(
    "fixture_name",
    ["docx_simple", "docx_with_table", "hwpx_simple"],
)
def test_ground_truth_exists_alongside(request: pytest.FixtureRequest, fixture_name: str) -> None:
    fixture_path: Path = request.getfixturevalue(fixture_name)
    gt = load_ground_truth(fixture_path)
    assert gt is not None, f"ground truth missing for {fixture_path}"
    assert "expected_format" in gt


def test_ground_truth_is_valid_json(docx_simple: Path) -> None:
    gt_path = docx_simple.with_name(docx_simple.name + ".gt.json")
    # Should round-trip
    parsed = json.loads(gt_path.read_text(encoding="utf-8"))
    assert parsed["expected_format"] == "docx"


def test_load_ground_truth_returns_none_when_missing(tmp_path: Path) -> None:
    no_gt = tmp_path / "lonely.docx"
    no_gt.write_bytes(b"PK\x03\x04")  # zip magic, contents irrelevant
    assert load_ground_truth(no_gt) is None


# ─────────────────────────────────────────────────────────────────────────────
# verify_against_ground_truth — happy path + each failure mode
# ─────────────────────────────────────────────────────────────────────────────


def _result(
    *,
    markdown: str = "# 제목\n본문",
    fmt: str = "docx",
    page_count: int | None = None,
    title: str | None = None,
    table_count: int = 0,
    image_count: int = 0,
    tmp_path: Path | None = None,
) -> ParseResult:
    """Build a synthetic ParseResult with controllable counts.

    ``table_count`` / ``image_count`` produce dummy entries since
    :func:`verify_against_ground_truth` only checks ``len(...)``.
    """
    from korean_doc_parser import ExtractedImage, ParsedTable

    return ParseResult(
        markdown=markdown,
        metadata=ParseMetadata(
            format=fmt,
            file_path=(tmp_path or Path()) / f"x.{fmt}",
            page_count=page_count,
            title=title,
        ),
        tables=[ParsedTable(rows=[["x"]]) for _ in range(table_count)],
        images=[
            ExtractedImage(
                page_no=None,
                section_no=None,
                bbox=None,
                bbox_unit="none",
                order_in_page=i,
                text_before="",
                text_after="",
                section_title=None,
                file_path="",
                sha256="",
                width=1,
                height=1,
                size_bytes=1,
                mime_type="image/png",
                detected_caption=None,
                caption_method=None,
                caption_pattern_score=0.0,
            )
            for i in range(image_count)
        ],
    )


def test_verify_passes_when_everything_matches() -> None:
    r = _result(markdown="# 제목\n본문 텍스트 입니다.", table_count=2, image_count=1)
    gt: GroundTruth = {
        "expected_format": "docx",
        "expected_table_count": 2,
        "expected_image_count": 1,
        "expected_sections": ["제목"],
        "expected_keywords": ["본문"],
        "expected_text_length_range": [5, 200],
    }
    verify_against_ground_truth(r, gt)


def test_verify_fails_on_format_mismatch() -> None:
    r = _result(fmt="pdf")
    gt: GroundTruth = {"expected_format": "docx"}
    with pytest.raises(AssertionError, match="format"):
        verify_against_ground_truth(r, gt)


def test_verify_fails_on_text_length_out_of_range() -> None:
    r = _result(markdown="짧음")
    gt: GroundTruth = {"expected_text_length_range": [100, 200]}
    with pytest.raises(AssertionError, match="length"):
        verify_against_ground_truth(r, gt)


def test_verify_fails_on_table_count_mismatch() -> None:
    r = _result(table_count=1)
    gt: GroundTruth = {"expected_table_count": 5}
    with pytest.raises(AssertionError, match="table count"):
        verify_against_ground_truth(r, gt)


def test_verify_fails_on_image_count_mismatch() -> None:
    r = _result(image_count=0)
    gt: GroundTruth = {"expected_image_count": 3}
    with pytest.raises(AssertionError, match="image count"):
        verify_against_ground_truth(r, gt)


def test_verify_fails_when_section_missing() -> None:
    r = _result(markdown="다른 본문")
    gt: GroundTruth = {"expected_sections": ["없는 섹션"]}
    with pytest.raises(AssertionError, match="missing sections"):
        verify_against_ground_truth(r, gt)


def test_verify_fails_when_keyword_missing() -> None:
    r = _result(markdown="다른 본문")
    gt: GroundTruth = {"expected_keywords": ["없는키워드"]}
    with pytest.raises(AssertionError, match="missing keywords"):
        verify_against_ground_truth(r, gt)


def test_verify_fails_on_page_count_mismatch() -> None:
    r = _result(page_count=3)
    gt: GroundTruth = {"expected_page_count": 5}
    with pytest.raises(AssertionError, match="page_count"):
        verify_against_ground_truth(r, gt)


def test_verify_fails_on_title_mismatch() -> None:
    r = _result(title="실제 제목")
    gt: GroundTruth = {"expected_title": "다른 제목"}
    with pytest.raises(AssertionError, match="title"):
        verify_against_ground_truth(r, gt)
