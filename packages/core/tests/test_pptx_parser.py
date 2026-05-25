"""Tests for the markitdown-backed PPTX parser (v0.3.0).

Coverage strategy:
* 4 synthetic fixtures (python-pptx-built) — title / multi-slide / table /
  image patterns. Always run in CI.
* 3 real fixtures (samples/, skip-guarded) — diverse domains: tour-corp
  proposal (37 slides), lets_portal tmp (42), QVAN storyboard (142).
* 1 corrupt fixture — 204-byte broken PPTX from real web upload, proves
  ParseError boundary.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from korean_doc_parser import ParseError, extract, get_parser, supported_extensions
from korean_doc_parser.parsers.pptx import PptxParser
from tests._gt import load_ground_truth, verify_against_ground_truth

# ─────────────────────────────────────────────────────────────────────────────
# Registration + extension handling
# ─────────────────────────────────────────────────────────────────────────────


def test_pptx_parser_is_auto_registered() -> None:
    parser = get_parser(".pptx")
    assert parser is not None
    assert isinstance(parser, PptxParser)


def test_pptx_parser_supported_extensions() -> None:
    assert PptxParser().supported_extensions == (".pptx",)


def test_supported_extensions_includes_pptx() -> None:
    assert ".pptx" in supported_extensions()


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic fixtures — ground-truth driven (always run, no samples/ dependency)
# ─────────────────────────────────────────────────────────────────────────────


def test_pptx_simple_matches_ground_truth(pptx_simple: Path) -> None:
    result = extract(pptx_simple)
    gt = load_ground_truth(pptx_simple)
    assert gt is not None
    verify_against_ground_truth(result, gt)


def test_pptx_simple_extracts_title(pptx_simple: Path) -> None:
    result = extract(pptx_simple)
    assert result.metadata.title == "합성 PPTX 단일 슬라이드"


def test_pptx_simple_emits_slide_marker(pptx_simple: Path) -> None:
    """markitdown emits ``<!-- Slide number: N -->`` per slide — useful for
    downstream RAG chunking. v0.3 contract pins this format."""
    result = extract(pptx_simple)
    assert "<!-- Slide number: 1 -->" in result.markdown


def test_pptx_multislide_emits_three_slide_markers(pptx_multislide: Path) -> None:
    result = extract(pptx_multislide)
    for n in (1, 2, 3):
        assert f"<!-- Slide number: {n} -->" in result.markdown


def test_pptx_multislide_matches_ground_truth(pptx_multislide: Path) -> None:
    result = extract(pptx_multislide)
    gt = load_ground_truth(pptx_multislide)
    assert gt is not None
    verify_against_ground_truth(result, gt)


def test_pptx_with_table_emits_markdown_table(pptx_with_table: Path) -> None:
    """v0.3 contract: tables stay inline in markdown (not in ParseResult.tables).
    Verify the markdown table divider syntax is present so downstream parsing
    is reliable."""
    result = extract(pptx_with_table)
    assert "| --- |" in result.markdown
    # Cells from the synthetic table must round-trip
    for cell in ("항목", "매출", "1,000", "고정비 포함"):
        assert cell in result.markdown


def test_pptx_with_table_matches_ground_truth(pptx_with_table: Path) -> None:
    result = extract(pptx_with_table)
    gt = load_ground_truth(pptx_with_table)
    assert gt is not None
    verify_against_ground_truth(result, gt)


def test_pptx_with_image_emits_placeholder(pptx_with_image: Path) -> None:
    """markitdown contract: images stay as ``![](filename)`` placeholders in
    the markdown stream — the bitmap is *additionally* extracted to
    ``ParseResult.images`` as of v0.4.4 (see the tests below)."""
    result = extract(pptx_with_image)
    assert "![" in result.markdown
    assert "이미지 포함 PPTX" in result.markdown


def test_pptx_with_image_matches_ground_truth(pptx_with_image: Path) -> None:
    result = extract(pptx_with_image)
    gt = load_ground_truth(pptx_with_image)
    assert gt is not None
    verify_against_ground_truth(result, gt)


# ─────────────────────────────────────────────────────────────────────────────
# Real-world fixtures — skip-guarded (samples/ untracked)
# ─────────────────────────────────────────────────────────────────────────────


def test_pptx_tour_corp_matches_ground_truth(pptx_tour_corp: Path) -> None:
    result = extract(pptx_tour_corp)
    gt = load_ground_truth(pptx_tour_corp)
    assert gt is not None
    verify_against_ground_truth(result, gt)


def test_pptx_letsportal_tmp_matches_ground_truth(pptx_letsportal_tmp: Path) -> None:
    result = extract(pptx_letsportal_tmp)
    gt = load_ground_truth(pptx_letsportal_tmp)
    assert gt is not None
    verify_against_ground_truth(result, gt)


def test_pptx_qvan_storyboard_matches_ground_truth(pptx_qvan_storyboard: Path) -> None:
    """Largest fixture (142 slides) — performance ceiling check."""
    result = extract(pptx_qvan_storyboard)
    gt = load_ground_truth(pptx_qvan_storyboard)
    assert gt is not None
    verify_against_ground_truth(result, gt)


def test_pptx_qvan_storyboard_extracts_korean_text(pptx_qvan_storyboard: Path) -> None:
    """Hangul ratio guard — mojibake regression on the largest real fixture."""
    result = extract(pptx_qvan_storyboard)
    hangul = sum(1 for c in result.markdown if 0xAC00 <= ord(c) <= 0xD7AF)
    assert hangul > len(result.markdown) * 0.2, (
        f"only {hangul}/{len(result.markdown)} Korean chars — encoding regression?"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Error path — real corrupt upload from web service
# ─────────────────────────────────────────────────────────────────────────────


def test_extract_raises_parse_error_on_vanasso_corrupt_upload(
    pptx_vanasso_corrupt: Path,
) -> None:
    """Real-world web upload regression — 204-byte truncated PPTX from
    vanasso.kr admin-uploads. The service must surface a clean ParseError,
    not crash. This guards the v0.3 contract for end users.

    Note: synthetic corrupt-bytes regression (the pattern used by pdf/docx/
    hwp tests) doesn't work for PPTX because markitdown's magika autodetect
    routes by content, not extension — random bytes get classified as a
    different file type and never reach the PPTX converter. The real
    truncated upload above ships enough structure to be misidentified
    correctly and surface the error.
    """
    with pytest.raises(ParseError, match="Failed to parse PPTX"):
        extract(pptx_vanasso_corrupt)


# ─────────────────────────────────────────────────────────────────────────────
# v0.4.4 — bitmap extraction via python-pptx (worklog/016)
# ─────────────────────────────────────────────────────────────────────────────


def test_pptx_with_image_extracts_one_bitmap(pptx_with_image: Path) -> None:
    """Synthetic fixture has a single 64x64 red PNG on slide 1 — must surface
    as one ``ExtractedImage`` with that exact size."""
    result = extract(pptx_with_image)
    assert len(result.images) == 1
    img = result.images[0]
    assert img.width == 64
    assert img.height == 64
    assert img.page_no == 1
    assert img.order_in_page == 1
    assert img.mime_type == "image/png"


def test_pptx_with_image_bitmap_persisted_to_disk(pptx_with_image: Path) -> None:
    """``file_path`` must point at a real tempfile that downstream Vision can
    open. ``sha256`` must be a 64-char hex string."""
    result = extract(pptx_with_image)
    img = result.images[0]
    assert Path(img.file_path).is_file()
    assert Path(img.file_path).stat().st_size == img.size_bytes
    assert len(img.sha256) == 64
    assert all(c in "0123456789abcdef" for c in img.sha256)


def test_pptx_simple_has_no_extracted_images(pptx_simple: Path) -> None:
    """Text-only synthetic PPTX must yield an empty image list (not crash)."""
    result = extract(pptx_simple)
    assert result.images == []


def test_pptx_multislide_has_no_extracted_images(pptx_multislide: Path) -> None:
    """Multi-slide text-only PPTX — empty image list across all slides."""
    result = extract(pptx_multislide)
    assert result.images == []


def test_pptx_with_image_bbox_in_emu(pptx_with_image: Path) -> None:
    """bbox is ``(left, top, right, bottom)`` in PPTX EMU (1 inch = 914400).
    The synthetic fixture places the image at Inches(1, 2) with Inches(1, 1)
    size → (914400, 1828800, 1828800, 2743200)."""
    result = extract(pptx_with_image)
    bbox = result.images[0].bbox
    assert bbox is not None
    left, top, right, bottom = bbox
    assert left == pytest.approx(914400)
    assert top == pytest.approx(1828800)
    assert right == pytest.approx(1828800)
    assert bottom == pytest.approx(2743200)
