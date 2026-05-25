"""Claude Vision prompts for Korean document image labelling (worklog/011 B.1).

v0.4 contract:
* 1-pass output: caption + image_type + confidence (always)
* 2-pass: confidence < THRESHOLD → re-call with reasoning request

Korean-only caption per B.3. image_type vocabulary is small + closed so
downstream filtering (e.g. RAG) gets predictable values.

Prompt caching strategy: the system prompt is invariant per model + threshold
combination, so Anthropic auto-cache kicks in. We don't manually mark
cache_control — letting the SDK auto-cache keeps prompts.py simple.
"""

from __future__ import annotations

from typing import Final, Literal

ImageType = Literal["chart", "photo", "diagram", "screenshot", "table", "logo", "other"]

# Vocabulary kept short + Korean-document-oriented. "table" is image-of-a-table
# (e.g. screenshot of a spreadsheet); structured tables are handled by core
# parsers (ParsedTable) and never reach Vision.
_IMAGE_TYPE_VALUES: Final[tuple[ImageType, ...]] = (
    "chart",
    "photo",
    "diagram",
    "screenshot",
    "table",
    "logo",
    "other",
)


SYSTEM_PROMPT_BASE: Final[str] = """당신은 한국 비즈니스 문서의 이미지를 분석하는 전문가입니다.
이미지를 보고 다음 정보를 JSON 으로 정확하게 출력하세요:

1. caption: 한국어 자연어 설명 (1-2문장, 30-100자).
   - 차트라면 "x축 / y축 / 핵심 데이터 추이" 위주
   - 사진이라면 "주요 피사체 / 배경 / 분위기" 위주
   - 다이어그램이라면 "구조 / 흐름 / 관계" 위주
2. image_type: chart / photo / diagram / screenshot / table / logo / other 중 하나
3. confidence: 본인 caption + image_type 판단의 확신도 (0.0-1.0)

JSON 외 다른 텍스트는 출력하지 마세요.
"""


SYSTEM_PROMPT_WITH_REASONING: Final[str] = (
    SYSTEM_PROMPT_BASE
    + """
4. reasoning: 위 판단의 근거 (1-3문장 한국어). 어떤 시각 단서가 분류/캡션을
   뒷받침하는지 설명하세요.
"""
)


def system_prompt(with_reasoning: bool) -> str:
    """Return the system prompt — short version (default) or with reasoning."""
    return SYSTEM_PROMPT_WITH_REASONING if with_reasoning else SYSTEM_PROMPT_BASE


USER_PROMPT: Final[str] = "이 이미지를 분석하고 위 JSON 형식으로 출력하세요."


def validate_image_type(value: str) -> ImageType:
    """Coerce model output to the closed vocabulary; fall back to 'other'."""
    v = (value or "").strip().lower()
    for known in _IMAGE_TYPE_VALUES:
        if v == known:
            return known
    return "other"


def validate_confidence(value: float | str | None) -> float:
    """Clamp model-reported confidence to [0.0, 1.0]; non-numeric → 0.5."""
    try:
        f = float(value) if value is not None else 0.5
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, f))
