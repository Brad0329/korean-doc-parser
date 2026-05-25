"""PII regex masking for Vision caption results (worklog/011 C.2).

This is the post-process mask — the image itself has already been sent to the
Anthropic API, so masking only protects the *returned text* (caption /
reasoning). Image-content PII detection would need OCR, which is permanently
out of scope (worklog/011 B.4).

Patterns are conservative — false positives are preferred to false negatives.
Add patterns over time as bidwatch / 사내 RAG flag misses.
"""

from __future__ import annotations

import re
from typing import Final

# Korean Resident Registration Number — XXXXXX-YYYYYYY (13 digits, dash)
_RRN_RE: Final[re.Pattern[str]] = re.compile(r"\b\d{6}[-\s]?\d{7}\b")

# Korean phone numbers — 010/011/016/017/018/019/02 + 7-8 digits
# Common written forms: 010-1234-5678 / 010 1234 5678 / 01012345678
_PHONE_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:0(?:1[016789]|2|3[1-3]|4[1-4]|5[1-5]|6[1-4]|7[0-9]|8[0-9]))"
    r"[-\s]?\d{3,4}[-\s]?\d{4}\b"
)

# Email — simple RFC-light pattern
_EMAIL_RE: Final[re.Pattern[str]] = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)


def mask_pii(text: str) -> str:
    """Return ``text`` with PII patterns replaced by stable masks.

    Replacements:
    * 주민번호 → ``XXXXXX-XXXXXXX``
    * 전화 → ``010-XXXX-XXXX``
    * 이메일 → ``XXX@XXX.XXX``

    Empty / None input passes through unchanged.
    """
    if not text:
        return text
    masked = _RRN_RE.sub("XXXXXX-XXXXXXX", text)
    masked = _PHONE_RE.sub("010-XXXX-XXXX", masked)
    masked = _EMAIL_RE.sub("XXX@XXX.XXX", masked)
    return masked
