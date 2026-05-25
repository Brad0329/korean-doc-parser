"""3-channel weighted confidence (worklog/011 § B, worklog/019 § 3-2).

Combines three independent signals into one auto-approve / needs-review
score:

* **regex** — caption pattern match (e.g. ``<그림 1>``, ``Figure 2``) score
* **proximity** — nearest-text-block distance score
* **vision** — Claude Vision's self-reported confidence

Default weights ``(0.4, 0.2, 0.4)`` are the worklog/011 § B values. Callers
override per workflow (e.g. HWP has no bbox → set proximity weight to 0 and
redistribute). Pure function: no I/O, no globals, no side effects.
"""

from __future__ import annotations

from typing import Final

DEFAULT_WEIGHTS: Final[tuple[float, float, float]] = (0.4, 0.2, 0.4)
"""``(regex, proximity, vision)`` — worklog/011 § B baseline."""


def weighted_confidence(
    *,
    regex_score: float,
    proximity_score: float,
    vision_confidence: float,
    weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
) -> float:
    """Blend three 0.0-1.0 signals into one 0.0-1.0 confidence.

    All inputs are clamped to ``[0.0, 1.0]`` — out-of-range inputs are
    treated as if the channel were silent at the appropriate extreme rather
    than raising, because upstream code routinely passes a default 0.0 for
    "no signal" and a future model might return slightly >1 from rounding.

    The weights are normalised at call time so callers can pass arbitrary
    positive numbers (e.g. ``(2, 1, 2)``) without pre-dividing. If all
    weights are zero the function returns 0.0 (rather than raising) — a
    "no signal" caller gets a "no confidence" result.
    """
    r = _clamp(regex_score)
    p = _clamp(proximity_score)
    v = _clamp(vision_confidence)
    wr, wp, wv = weights
    total = wr + wp + wv
    if total <= 0:
        return 0.0
    return (r * wr + p * wp + v * wv) / total


def _clamp(value: float) -> float:
    """Squeeze ``value`` into ``[0.0, 1.0]``."""
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value
