"""Caption 1차 검출 — 결정론적 (deterministic) regex + bbox proximity.

The two functions in this module are the engine-side caption detectors —
they run *before* any Vision call, so the cheap signals (caption number
patterns, nearest-text-block distance) are available for the
:func:`~korean_doc_parser.pipeline.confidence.weighted_confidence` blend.

Patterns covered (worklog/019 § 6-2):

* Korean: ``<그림 1>`` / ``[그림 1]`` / ``그림 1`` / ``<표 1>`` / ``[표 1]`` / ``표 1``
* English: ``Figure 1`` / ``Fig. 1`` / ``Table 1``
* Sources: ``자료: ...`` / ``출처: ...`` (frequent in 정부/공공 PDFs)

The regex detector returns the **whole line** containing the match as the
caption candidate; refinement (stripping the label, joining with the next
line, etc.) is left to v1.0+ as the cost of being wrong here is low —
downstream Vision still sees the image.

The proximity detector is bbox-unit-agnostic: distances are computed in
whatever unit the caller supplies, and the score is purely a *relative*
ranking inside one call. Callers must keep ``image_bbox`` and ``text_blocks``
bboxes in the **same unit** (px / EMU / etc.) — see ``ExtractedImage.bbox_unit``
once that field lands.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

# ─────────────────────────────────────────────────────────────────────────────
# Regex detector
# ─────────────────────────────────────────────────────────────────────────────

# Each pattern captures the *whole line* containing the marker — multiline
# mode + a line-anchored body. The match score reflects how prescriptive the
# marker is: bracketed forms (``<그림 1>``) are stronger than bare prefixes.
_CAPTION_PATTERNS: Final[list[tuple[re.Pattern[str], float]]] = [
    # Strong markers — bracketed Korean labels
    (re.compile(r"^[^\n]*<\s*(?:그림|표|그래프|도표)\s*\d+[^\n>]*>[^\n]*$", re.MULTILINE), 1.0),
    (re.compile(r"^[^\n]*\[\s*(?:그림|표|그래프|도표)\s*\d+[^\n\]]*\][^\n]*$", re.MULTILINE), 1.0),
    # Strong markers — English bracketed
    (
        re.compile(
            r"^[^\n]*(?:Figure|Fig\.?|Table)\s*\d+\s*[:.][^\n]*$", re.MULTILINE | re.IGNORECASE
        ),
        0.95,
    ),
    # Medium — bare Korean prefix
    (re.compile(r"^\s*(?:그림|표|그래프|도표)\s*\d+[\s.:][^\n]*$", re.MULTILINE), 0.85),
    # Medium — bare English prefix
    (
        re.compile(r"^\s*(?:Figure|Fig\.?|Table)\s*\d+[\s.:][^\n]*$", re.MULTILINE | re.IGNORECASE),
        0.85,
    ),
    # Weak — source attribution lines (still useful as a caption candidate)
    # The character class matches either ASCII colon or fullwidth U+FF1A —
    # Korean public-domain PDFs use both. ruff's ambiguity warning is silenced
    # because the fullwidth form is deliberate.
    (
        re.compile(
            r"^\s*(?:자료|출처|Source)\s*[:：][^\n]+$",  # noqa: RUF001 — fullwidth colon deliberate
            re.MULTILINE | re.IGNORECASE,
        ),
        0.6,
    ),
]


def detect_caption_regex(text: str) -> tuple[str | None, float]:
    """Find the strongest caption marker in ``text``.

    Returns ``(line, score)`` — ``line`` is the matched line stripped of
    surrounding whitespace; ``score`` is in ``[0.0, 1.0]`` per the pattern
    strength table above. Returns ``(None, 0.0)`` when no pattern matches
    (e.g. body text only).

    When several patterns match different lines, the first match of the
    highest-scoring pattern wins — this favours explicit ``<그림 N>`` over
    a generic ``자료: ...`` even if both appear.
    """
    if not text:
        return None, 0.0
    best: tuple[str | None, float] = (None, 0.0)
    for pattern, score in _CAPTION_PATTERNS:
        if score <= best[1]:
            # Subsequent patterns can't beat what we already have.
            break
        match = pattern.search(text)
        if match:
            best = (match.group(0).strip(), score)
    return best


# ─────────────────────────────────────────────────────────────────────────────
# Proximity detector
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TextBlock:
    """One text region with its bbox in the caller's unit.

    Same shape as ``ExtractedImage.bbox`` — ``(left, top, right, bottom)``.
    Callers feed this from their parser's text-layout pass (pdfplumber
    ``chars`` regions, python-pptx shape text frames, etc.).
    """

    text: str
    bbox: tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class CaptionDetection:
    """Result of one proximity lookup — ``text`` may be ``None`` on no hit."""

    text: str | None
    score: float
    distance: float  # 0.0 = bbox center == image center; higher = farther


def detect_caption_proximity(
    image_bbox: tuple[float, float, float, float] | None,
    text_blocks: list[TextBlock],
    *,
    max_distance: float | None = None,
) -> tuple[str | None, float]:
    """Return the nearest text block's text + a 0.0-1.0 proximity score.

    Distance is between bbox **centers**. The score is computed as
    ``1.0 / (1.0 + distance / scale)`` where ``scale`` is the average of
    the image bbox's width and height — this normalises the score so a
    text block sitting roughly one image-width away gets ~0.5, regardless
    of whether the units are pixels (PDF) or EMU (PPTX).

    Returns ``(None, 0.0)`` when ``image_bbox`` is ``None`` (HWP, DOCX in
    current parsers) or ``text_blocks`` is empty. ``max_distance``, when
    set, hard-caps which blocks are considered — useful to suppress
    "caption from another column" hits in multi-column PDFs.
    """
    if image_bbox is None or not text_blocks:
        return None, 0.0
    ix, iy = _center(image_bbox)
    iw = image_bbox[2] - image_bbox[0]
    ih = image_bbox[3] - image_bbox[1]
    scale = max((iw + ih) / 2.0, 1.0)  # avoid divide-by-zero on degenerate bboxes

    best_block: TextBlock | None = None
    best_distance = float("inf")
    for block in text_blocks:
        bx, by = _center(block.bbox)
        d = ((bx - ix) ** 2 + (by - iy) ** 2) ** 0.5
        if max_distance is not None and d > max_distance:
            continue
        if d < best_distance:
            best_distance = d
            best_block = block

    if best_block is None:
        return None, 0.0
    score = 1.0 / (1.0 + best_distance / scale)
    return best_block.text, score


def _center(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    """``(cx, cy)`` for an ``(l, t, r, b)`` bbox."""
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
