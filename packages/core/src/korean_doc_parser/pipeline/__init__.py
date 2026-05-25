"""Stateless algorithm helpers for downstream pipelines (v0.5.0, worklog/019).

This sub-package collects pure functions that downstream services (bidwatch /
vanasso.kr / 사내 RAG) use to compose document ingestion flows around
``korean_doc_parser``. Per worklog/019, the package is **stateless on
purpose**: no DB, no queue, no UI — those belong to the caller. Each helper
is a pure function, safe to import in any context.

Public surface:

* :func:`compute_doc_id` — sha256 of file bytes → primary key candidate
* :func:`weighted_confidence` — 3-channel weighted score
  (regex / proximity / vision) per worklog/011 § B
* :func:`detect_caption_regex` — Korean / English caption pattern matching
* :func:`detect_caption_proximity` — bbox distance → nearest text block

Callers populate :class:`korean_doc_parser.ExtractedImage` fields
(``detected_caption`` / ``caption_method`` / ``caption_pattern_score``)
themselves; the helpers don't mutate parser output. This keeps the engine /
pipeline boundary clean (HANDOVER § 2-1).
"""

from __future__ import annotations

from korean_doc_parser.pipeline.caption import (
    CaptionDetection,
    TextBlock,
    detect_caption_proximity,
    detect_caption_regex,
)
from korean_doc_parser.pipeline.confidence import (
    DEFAULT_WEIGHTS,
    weighted_confidence,
)
from korean_doc_parser.pipeline.doc_id import compute_doc_id

__all__ = [
    "DEFAULT_WEIGHTS",
    "CaptionDetection",
    "TextBlock",
    "compute_doc_id",
    "detect_caption_proximity",
    "detect_caption_regex",
    "weighted_confidence",
]
