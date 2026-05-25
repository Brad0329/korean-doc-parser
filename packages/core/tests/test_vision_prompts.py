"""Prompt + output validation unit tests (worklog/011 B.1)."""

from __future__ import annotations

import pytest

from korean_doc_parser.vision.prompts import (
    SYSTEM_PROMPT_BASE,
    SYSTEM_PROMPT_WITH_REASONING,
    system_prompt,
    validate_confidence,
    validate_image_type,
)


def test_system_prompt_short_excludes_reasoning() -> None:
    p = system_prompt(with_reasoning=False)
    assert "caption" in p
    assert "image_type" in p
    assert "confidence" in p
    assert "reasoning" not in p
    assert p == SYSTEM_PROMPT_BASE


def test_system_prompt_with_reasoning_includes_all_four() -> None:
    p = system_prompt(with_reasoning=True)
    assert "caption" in p
    assert "image_type" in p
    assert "confidence" in p
    assert "reasoning" in p
    assert p == SYSTEM_PROMPT_WITH_REASONING


def test_korean_in_prompt() -> None:
    p = SYSTEM_PROMPT_BASE
    hangul = sum(1 for c in p if 0xAC00 <= ord(c) <= 0xD7AF)
    assert hangul > 30  # Korean-only mandate (B.3)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("chart", "chart"),
        ("CHART", "chart"),
        ("photo", "photo"),
        ("unknown_type", "other"),
        ("", "other"),
    ],
)
def test_validate_image_type(value: str, expected: str) -> None:
    assert validate_image_type(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (0.8, 0.8),
        ("0.65", 0.65),
        (1.5, 1.0),  # clamp upper
        (-0.1, 0.0),  # clamp lower
        ("invalid", 0.5),  # fallback
        (None, 0.5),
    ],
)
def test_validate_confidence(value: object, expected: float) -> None:
    assert validate_confidence(value) == pytest.approx(expected)  # type: ignore[arg-type]
