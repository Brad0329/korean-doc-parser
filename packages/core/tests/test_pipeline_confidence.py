"""``korean_doc_parser.pipeline.confidence`` — 3-channel weighted score (v0.5.0)."""

from __future__ import annotations

import pytest

from korean_doc_parser.pipeline import DEFAULT_WEIGHTS, weighted_confidence


def test_default_weights_match_worklog_011_section_b() -> None:
    """The baseline (0.4, 0.2, 0.4) is documented — guard against accidental
    silent change."""
    assert DEFAULT_WEIGHTS == (0.4, 0.2, 0.4)


def test_all_zero_inputs_give_zero() -> None:
    assert weighted_confidence(regex_score=0, proximity_score=0, vision_confidence=0) == 0.0


def test_all_one_inputs_give_one() -> None:
    assert weighted_confidence(regex_score=1, proximity_score=1, vision_confidence=1) == 1.0


def test_default_blend_matches_manual_calc() -> None:
    """Sanity: 0.4*0.8 + 0.2*0.5 + 0.4*0.9 / total → 0.78."""
    got = weighted_confidence(regex_score=0.8, proximity_score=0.5, vision_confidence=0.9)
    assert got == pytest.approx(0.78, rel=1e-3)


def test_inputs_above_1_are_clamped() -> None:
    """Future-proofing — a model returning 1.0001 should not propagate."""
    got = weighted_confidence(regex_score=10, proximity_score=10, vision_confidence=10)
    assert got == 1.0


def test_inputs_below_0_are_clamped() -> None:
    got = weighted_confidence(regex_score=-1, proximity_score=-2, vision_confidence=-3)
    assert got == 0.0


def test_custom_weights_redistribute() -> None:
    """HWP usecase: no bbox → proximity weight = 0, redistribute to (0.5, 0, 0.5)."""
    got = weighted_confidence(
        regex_score=0.6,
        proximity_score=0.0,  # ignored
        vision_confidence=0.8,
        weights=(0.5, 0.0, 0.5),
    )
    assert got == pytest.approx(0.7, rel=1e-3)


def test_arbitrary_positive_weights_are_normalised() -> None:
    """Callers can pass (2, 1, 2) without pre-normalising."""
    got_norm = weighted_confidence(
        regex_score=0.8, proximity_score=0.5, vision_confidence=0.9, weights=(2, 1, 2)
    )
    got_default = weighted_confidence(
        regex_score=0.8, proximity_score=0.5, vision_confidence=0.9, weights=(0.4, 0.2, 0.4)
    )
    assert got_norm == pytest.approx(got_default, rel=1e-6)


def test_zero_weight_sum_returns_zero_no_zerodivision() -> None:
    """No raise on (0, 0, 0) — silent caller gets no-confidence result."""
    got = weighted_confidence(
        regex_score=0.9, proximity_score=0.9, vision_confidence=0.9, weights=(0, 0, 0)
    )
    assert got == 0.0
