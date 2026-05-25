"""Claude Vision labelling for ExtractedImage — v0.4 opt-in extras.

Decisions live in ``worklog/011_v0.4_decision_matrix.md``:
* A.1 model = Sonnet (with Haiku comparison in eval)
* B.1 4-field 2-pass (caption + type + confidence always, reasoning only when
  confidence < 0.7)
* B.2 bitmap only, >= 100x100 px
* B.3 Korean-only caption
* C.2 caption-result regex masking for PII
* C.4 sha256+model cache (SQLite in v0.4, PostgreSQL in v0.5)

Public API kept tiny — the CLI (``cli/label.py``) is the user-facing entry.
"""

from __future__ import annotations

from korean_doc_parser.vision.client import VisionClient, VisionResult

__all__ = [
    "VisionClient",
    "VisionResult",
]
