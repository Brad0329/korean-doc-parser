"""VisionClient with mocked Anthropic SDK (no real API calls)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from korean_doc_parser.vision.cache import VisionCache
from korean_doc_parser.vision.client import VisionClient, _parse_json_reply

# ─── Fake Anthropic SDK building blocks ──────────────────────────────────────


@dataclass
class _FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class _FakeContent:
    text: str


@dataclass
class _FakeMessage:
    content: list[_FakeContent]
    usage: _FakeUsage


class _FakeMessages:
    """Replaces ``client.messages``. Returns scripted replies in order."""

    def __init__(self, replies: list[tuple[dict[str, Any], _FakeUsage]]) -> None:
        self._replies = list(replies)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _FakeMessage:
        self.calls.append(kwargs)
        reply, usage = self._replies.pop(0)
        return _FakeMessage(
            content=[_FakeContent(text=json.dumps(reply, ensure_ascii=False))],
            usage=usage,
        )


class _FakeAnthropic:
    def __init__(self, replies: list[tuple[dict[str, Any], _FakeUsage]]) -> None:
        self.messages = _FakeMessages(replies)


# ─── Test fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def tiny_png(tmp_path: Path) -> Path:
    """8x8 red PNG for cheap labelling tests."""
    p = tmp_path / "tiny.png"
    Image.new("RGB", (8, 8), (255, 0, 0)).save(p, format="PNG")
    return p


@pytest.fixture
def cache(tmp_path: Path) -> VisionCache:
    return VisionCache(tmp_path / "cache.db")


# ─── Tests ───────────────────────────────────────────────────────────────────


def test_high_confidence_single_pass(
    monkeypatch: pytest.MonkeyPatch, tiny_png: Path, cache: VisionCache
) -> None:
    """confidence >= threshold → 1 API call, no reasoning."""
    fake = _FakeAnthropic(
        replies=[
            (
                {"caption": "빨간 정사각형", "image_type": "photo", "confidence": 0.92},
                _FakeUsage(input_tokens=1500, output_tokens=50),
            )
        ]
    )

    client = VisionClient(model="claude-sonnet-4-5", cache=cache, reasoning_threshold=0.7)
    monkeypatch.setattr(client, "_client", lambda: fake)

    result = client.label(tiny_png)
    assert result.caption == "빨간 정사각형"
    assert result.image_type == "photo"
    assert result.confidence == pytest.approx(0.92)
    assert result.reasoning is None
    assert result.second_pass is False
    assert result.cache_hit is False
    assert len(fake.messages.calls) == 1


def test_low_confidence_triggers_second_pass(
    monkeypatch: pytest.MonkeyPatch, tiny_png: Path, cache: VisionCache
) -> None:
    """confidence < threshold → 2nd API call with reasoning."""
    fake = _FakeAnthropic(
        replies=[
            (
                {"caption": "흐릿한 이미지", "image_type": "other", "confidence": 0.45},
                _FakeUsage(input_tokens=1500, output_tokens=50),
            ),
            (
                {
                    "caption": "흐릿한 사진",
                    "image_type": "photo",
                    "confidence": 0.55,
                    "reasoning": "단색 영역이 많아 사진으로 추정.",
                },
                _FakeUsage(input_tokens=1700, output_tokens=200),
            ),
        ]
    )

    client = VisionClient(model="claude-sonnet-4-5", cache=cache, reasoning_threshold=0.7)
    monkeypatch.setattr(client, "_client", lambda: fake)

    result = client.label(tiny_png)
    assert result.second_pass is True
    assert result.reasoning == "단색 영역이 많아 사진으로 추정."
    assert result.image_type == "photo"  # refined by 2nd pass
    assert result.input_tokens == 1500 + 1700  # both calls accounted
    assert result.output_tokens == 50 + 200
    assert len(fake.messages.calls) == 2


def test_cache_hit_skips_api(
    monkeypatch: pytest.MonkeyPatch, tiny_png: Path, cache: VisionCache
) -> None:
    """2nd call with same sha+model returns cached value, no API call."""
    fake = _FakeAnthropic(
        replies=[
            (
                {"caption": "빨강", "image_type": "photo", "confidence": 0.91},
                _FakeUsage(input_tokens=1500, output_tokens=40),
            )
        ]
    )
    client = VisionClient(model="claude-sonnet-4-5", cache=cache, reasoning_threshold=0.7)
    monkeypatch.setattr(client, "_client", lambda: fake)

    first = client.label(tiny_png)
    second = client.label(tiny_png)

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert second.caption == first.caption
    assert len(fake.messages.calls) == 1  # 2nd call hit cache


def test_pii_in_caption_is_masked(
    monkeypatch: pytest.MonkeyPatch, tiny_png: Path, cache: VisionCache
) -> None:
    """C.2 — caption-result PII patterns are masked."""
    fake = _FakeAnthropic(
        replies=[
            (
                {
                    "caption": "담당자 010-1234-5678 의 연락처",
                    "image_type": "screenshot",
                    "confidence": 0.85,
                },
                _FakeUsage(input_tokens=1500, output_tokens=80),
            )
        ]
    )
    client = VisionClient(model="claude-sonnet-4-5", cache=cache, reasoning_threshold=0.7)
    monkeypatch.setattr(client, "_client", lambda: fake)

    result = client.label(tiny_png)
    assert "010-1234-5678" not in result.caption
    assert "010-XXXX-XXXX" in result.caption


def test_invalid_json_falls_back_gracefully(
    monkeypatch: pytest.MonkeyPatch, tiny_png: Path, cache: VisionCache
) -> None:
    """Malformed model output → fallback values, no crash."""

    class _NonJsonMessages:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        def create(self, **kwargs: Any) -> _FakeMessage:
            self.calls.append(kwargs)
            return _FakeMessage(
                content=[_FakeContent(text="죄송합니다 — 분석할 수 없습니다")],
                usage=_FakeUsage(input_tokens=1500, output_tokens=20),
            )

    class _Stub:
        def __init__(self) -> None:
            self.messages = _NonJsonMessages()

    stub = _Stub()
    client = VisionClient(model="claude-sonnet-4-5", cache=cache, reasoning_threshold=0.7)
    monkeypatch.setattr(client, "_client", lambda: stub)

    result = client.label(tiny_png)
    assert result.image_type == "other"
    assert result.confidence == 0.0
    # confidence 0 < 0.7 → second pass attempted (which also fails JSON parse).
    # The fallback values from the parser keep the result stable.
    assert result.second_pass is True
    assert len(stub.messages.calls) == 2


def test_no_cache_mode_does_not_persist(monkeypatch: pytest.MonkeyPatch, tiny_png: Path) -> None:
    """Client without cache argument never reads/writes."""
    fake = _FakeAnthropic(
        replies=[
            (
                {"caption": "테스트", "image_type": "photo", "confidence": 0.9},
                _FakeUsage(input_tokens=1500, output_tokens=40),
            ),
            (
                {"caption": "테스트2", "image_type": "photo", "confidence": 0.9},
                _FakeUsage(input_tokens=1500, output_tokens=40),
            ),
        ]
    )
    client = VisionClient(model="claude-sonnet-4-5", cache=None)
    monkeypatch.setattr(client, "_client", lambda: fake)

    first = client.label(tiny_png)
    second = client.label(tiny_png)
    assert first.cache_hit is False
    assert second.cache_hit is False  # no cache → re-call


def test_parse_json_reply_strips_markdown_fences() -> None:
    """Models sometimes wrap JSON in ```json ... ```."""
    reply = '```json\n{"caption": "테스트", "image_type": "chart", "confidence": 0.9}\n```'
    parsed = _parse_json_reply(reply)
    assert parsed["caption"] == "테스트"


def test_parse_json_reply_handles_empty_string() -> None:
    parsed = _parse_json_reply("")
    assert parsed["caption"] == ""
    assert parsed["confidence"] == 0.0


# Silence unused-import warning (Image, BytesIO held for ergonomics)
_ = BytesIO
