"""``korean_doc_parser.pipeline.caption`` — regex + proximity tests (v0.5.0)."""

from __future__ import annotations

import pytest

from korean_doc_parser.pipeline import (
    TextBlock,
    detect_caption_proximity,
    detect_caption_regex,
)

# ─────────────────────────────────────────────────────────────────────────────
# Regex detector
# ─────────────────────────────────────────────────────────────────────────────


def test_regex_no_match_returns_none() -> None:
    caption, score = detect_caption_regex("그냥 본문 텍스트입니다. 매칭될 패턴 없음.")
    assert caption is None
    assert score == 0.0


def test_regex_empty_text_returns_none() -> None:
    caption, score = detect_caption_regex("")
    assert caption is None
    assert score == 0.0


@pytest.mark.parametrize(
    "text,expected_in_caption",
    [
        ("<그림 1> 매출 추이", "<그림 1>"),
        ("<표 3> 매출 항목별 비중", "<표 3>"),
        ("<그래프 2> Q2 실적", "<그래프 2>"),
    ],
)
def test_regex_bracketed_korean_strong_match(text: str, expected_in_caption: str) -> None:
    """Strong markers (``<...>``) score 1.0."""
    caption, score = detect_caption_regex(text)
    assert caption is not None
    assert expected_in_caption in caption
    assert score == 1.0


@pytest.mark.parametrize("text", ["[그림 5] 손익분기점", "[표 2] 비용 항목"])
def test_regex_square_bracket_korean_match(text: str) -> None:
    caption, score = detect_caption_regex(text)
    assert caption is not None
    assert score == 1.0


def test_regex_english_figure_match() -> None:
    caption, score = detect_caption_regex("Figure 1: Revenue trend over five years")
    assert caption is not None
    assert "Figure 1" in caption
    assert score >= 0.85


def test_regex_english_table_match() -> None:
    caption, score = detect_caption_regex("Table 4. Comparison of three methods")
    assert caption is not None
    assert score >= 0.85


def test_regex_source_attribution_weak_match() -> None:
    """``자료: ...`` is a weaker but valid caption candidate (score ≤ 0.7)."""
    caption, score = detect_caption_regex("자료: 한국은행 (2025)")
    assert caption is not None
    assert "자료" in caption
    assert 0.5 <= score <= 0.7


def test_regex_fullwidth_colon_source() -> None:
    """Korean PDFs often use the fullwidth colon (U+FF1A)."""
    caption, score = detect_caption_regex("출처：통계청 2024년 자료")  # noqa: RUF001
    assert caption is not None
    assert score > 0.0


def test_regex_picks_strongest_when_multiple_patterns_match() -> None:
    """``<그림 1>`` (1.0) should win over ``자료: ...`` (0.6) in the same text."""
    text = "자료: 한국은행 (2025)\n<그림 1> 매출 추이"
    caption, score = detect_caption_regex(text)
    assert caption is not None
    assert "그림 1" in caption
    assert score == 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Proximity detector
# ─────────────────────────────────────────────────────────────────────────────


def test_proximity_none_bbox_returns_none() -> None:
    """HWP / DOCX (bbox=None) callers get an explicit no-result."""
    caption, score = detect_caption_proximity(None, [TextBlock("any", (0, 0, 10, 10))])
    assert caption is None
    assert score == 0.0


def test_proximity_empty_blocks_returns_none() -> None:
    caption, score = detect_caption_proximity((0, 0, 100, 100), [])
    assert caption is None
    assert score == 0.0


def test_proximity_picks_closest_block_by_center() -> None:
    img = (100.0, 100.0, 200.0, 200.0)  # center (150, 150)
    blocks = [
        TextBlock("far away", (0, 0, 10, 10)),  # center (5, 5)
        TextBlock("right next to image", (210, 100, 310, 200)),  # center (260, 150)
        TextBlock("medium distance", (100, 250, 200, 280)),  # center (150, 265)
    ]
    caption, score = detect_caption_proximity(img, blocks)
    assert caption == "right next to image"
    assert 0.0 < score <= 1.0


def test_proximity_score_decreases_with_distance() -> None:
    img = (0.0, 0.0, 10.0, 10.0)
    close = TextBlock("close", (12, 0, 22, 10))  # center distance ~12 from (5,5) → 12
    far = TextBlock("far", (200, 0, 210, 10))  # distance ~200
    _, score_close = detect_caption_proximity(img, [close])
    _, score_far = detect_caption_proximity(img, [far])
    assert score_close > score_far


def test_proximity_max_distance_filter() -> None:
    img = (0.0, 0.0, 10.0, 10.0)
    blocks = [TextBlock("too far", (1000, 1000, 1010, 1010))]
    caption, score = detect_caption_proximity(img, blocks, max_distance=100)
    assert caption is None
    assert score == 0.0


def test_proximity_unit_agnostic_emu_vs_px() -> None:
    """Relative ranking inside one call shouldn't depend on the unit — same
    layout in EMU and px should pick the same block."""
    # px coords (small numbers)
    img_px = (100.0, 100.0, 200.0, 200.0)
    blocks_px = [
        TextBlock("near", (210, 100, 310, 200)),
        TextBlock("far", (1000, 1000, 1100, 1100)),
    ]
    # EMU equivalent (1px ≈ 9525 EMU at 96 DPI)
    img_emu = (100 * 9525.0, 100 * 9525.0, 200 * 9525.0, 200 * 9525.0)
    blocks_emu = [
        TextBlock("near", (210 * 9525.0, 100 * 9525.0, 310 * 9525.0, 200 * 9525.0)),
        TextBlock("far", (1000 * 9525.0, 1000 * 9525.0, 1100 * 9525.0, 1100 * 9525.0)),
    ]
    cap_px, _ = detect_caption_proximity(img_px, blocks_px)
    cap_emu, _ = detect_caption_proximity(img_emu, blocks_emu)
    assert cap_px == cap_emu == "near"


def test_proximity_score_in_valid_range() -> None:
    img = (0.0, 0.0, 10.0, 10.0)
    blocks = [TextBlock("x", (0, 0, 10, 10))]
    _, score = detect_caption_proximity(img, blocks)
    assert 0.0 <= score <= 1.0
