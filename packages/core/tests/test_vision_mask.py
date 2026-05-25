"""PII masking unit tests (worklog/011 C.2)."""

from __future__ import annotations

import pytest

from korean_doc_parser.vision.mask import mask_pii


def test_passthrough_empty() -> None:
    assert mask_pii("") == ""


def test_passthrough_plain_korean() -> None:
    text = "매출 추이를 보여주는 막대 그래프입니다."
    assert mask_pii(text) == text


@pytest.mark.parametrize(
    "raw",
    [
        "주민번호 880101-1234567 입니다",
        "연락처: 8801011234567",
        "880101 1234567",
    ],
)
def test_rrn_masked(raw: str) -> None:
    assert "XXXXXX-XXXXXXX" in mask_pii(raw)
    # Original digits should be gone
    assert "880101" not in mask_pii(raw)


@pytest.mark.parametrize(
    "raw",
    [
        "010-1234-5678",
        "010 1234 5678",
        "01012345678",
        "02-555-1234",
    ],
)
def test_phone_masked(raw: str) -> None:
    assert "010-XXXX-XXXX" in mask_pii(raw)


def test_email_masked() -> None:
    text = "문의: hello@example.com"
    masked = mask_pii(text)
    assert "hello@example.com" not in masked
    assert "XXX@XXX.XXX" in masked


def test_multiple_pii_in_same_caption() -> None:
    text = "담당자 hong@test.kr (010-9999-1234), 등록번호 901231-1234567"
    masked = mask_pii(text)
    assert "hong@test.kr" not in masked
    assert "010-9999-1234" not in masked
    assert "901231-1234567" not in masked
    assert "XXX@XXX.XXX" in masked
    assert "010-XXXX-XXXX" in masked
    assert "XXXXXX-XXXXXXX" in masked


def test_no_false_positive_on_simple_numbers() -> None:
    # 6 digits alone shouldn't trigger RRN; 4 digits alone shouldn't trigger phone
    text = "2024년 매출은 1000억 원입니다."
    assert mask_pii(text) == text
