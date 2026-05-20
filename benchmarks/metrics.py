"""Scoring helpers for benchmark output vs ground-truth JSON.

Ground-truth schema (per fixture, alongside the file as `<stem>.gt.json`):

    {
      "expected_keywords": ["입찰공고", "낙찰자", "예정가격"],
      "expected_table_count": 3,
      "expected_image_count": 2,
      "expected_text_length_range": [1500, 8000],
      "tolerance": {"table": 1, "image": 2}   // optional
    }

All scores are in [0.0, 1.0]. Missing GT keys are skipped (return None) so the
report can show "n/a" rather than a misleading zero.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class FixtureMetrics:
    keyword_recall: Optional[float] = None
    matched_keywords: Optional[int] = None
    expected_keywords: Optional[int] = None
    table_accuracy: Optional[float] = None
    image_accuracy: Optional[float] = None
    text_length_in_range: Optional[float] = None
    composite: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


def load_ground_truth(fixture_path: Path) -> Optional[dict]:
    gt_path = fixture_path.with_suffix(fixture_path.suffix + ".gt.json")
    if gt_path.is_file():
        return json.loads(gt_path.read_text(encoding="utf-8"))
    gt_path_alt = fixture_path.with_suffix(".gt.json")
    if gt_path_alt.is_file():
        return json.loads(gt_path_alt.read_text(encoding="utf-8"))
    return None


def score(text: str, table_count: int, image_count: int, gt: dict) -> FixtureMetrics:
    m = FixtureMetrics()
    tol = gt.get("tolerance", {})

    if "expected_keywords" in gt:
        kws = gt["expected_keywords"]
        m.expected_keywords = len(kws)
        m.matched_keywords = sum(1 for kw in kws if kw in text)
        m.keyword_recall = (m.matched_keywords / m.expected_keywords) if kws else None

    if "expected_table_count" in gt:
        m.table_accuracy = _count_accuracy(
            actual=table_count,
            expected=gt["expected_table_count"],
            tolerance=tol.get("table", 1),
        )

    if "expected_image_count" in gt:
        m.image_accuracy = _count_accuracy(
            actual=image_count,
            expected=gt["expected_image_count"],
            tolerance=tol.get("image", 2),
        )

    if "expected_text_length_range" in gt:
        lo, hi = gt["expected_text_length_range"]
        m.text_length_in_range = 1.0 if lo <= len(text) <= hi else 0.0

    parts = [
        x
        for x in (m.keyword_recall, m.table_accuracy, m.image_accuracy, m.text_length_in_range)
        if x is not None
    ]
    m.composite = sum(parts) / len(parts) if parts else None
    return m


def _count_accuracy(actual: int, expected: int, tolerance: int) -> float:
    """1.0 if |actual - expected| <= tolerance, else linearly decay to 0.

    The decay rule penalizes large misses but does not collapse to 0 for being
    one off when tolerance=0, which keeps the score readable.
    """
    diff = abs(actual - expected)
    if diff <= tolerance:
        return 1.0
    denom = max(expected, 1) * 2
    return max(0.0, 1.0 - (diff - tolerance) / denom)
