"""Ground-truth helpers for fixture-driven tests.

Convention (CLAUDE.md §"Ground truth JSON"):
each fixture ``foo.<ext>`` may have a sibling ``foo.<ext>.gt.json`` describing
the expected parse result. Loading + verifying is centralized here so per-
parser tests stay short.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from korean_doc_parser import ParseResult

__all__ = [
    "GroundTruth",
    "load_ground_truth",
    "verify_against_ground_truth",
]


class GroundTruth(TypedDict, total=False):
    """Expected parse output for a single fixture.

    Every field is optional — a test should only assert what it cares about.
    Range fields (``expected_text_length_range``) accept a 2-tuple ``[lo, hi]``
    and treat both bounds as inclusive.
    """

    expected_format: str  # e.g. "pdf", "hwp" — lowercase, no leading dot
    expected_page_count: int
    expected_text_length_range: list[int]  # [lo, hi], inclusive
    expected_table_count: int
    expected_image_count: int
    expected_sections: list[str]  # substrings that must appear in markdown
    expected_keywords: list[str]  # substrings that must appear in markdown
    expected_title: str


def load_ground_truth(fixture_path: Path) -> GroundTruth | None:
    """Return the ground truth dict for ``fixture_path``, or ``None`` if absent.

    Looks for ``<fixture>.gt.json`` (e.g. ``simple.docx`` → ``simple.docx.gt.json``).
    Reads as UTF-8 with strict JSON.
    """
    gt_path = fixture_path.with_name(fixture_path.name + ".gt.json")
    if not gt_path.is_file():
        return None
    return json.loads(gt_path.read_text(encoding="utf-8"))


def verify_against_ground_truth(result: ParseResult, gt: GroundTruth) -> None:
    """Assert ``result`` matches every populated field of ``gt``.

    Raises ``AssertionError`` on the first mismatch with a descriptive message.
    Fields not present in ``gt`` are skipped (forward-compatible).
    """
    if "expected_format" in gt:
        actual = result.metadata.format
        expected = gt["expected_format"]
        assert actual == expected, f"format: expected {expected!r}, got {actual!r}"

    if "expected_page_count" in gt:
        actual_pc = result.metadata.page_count
        expected_pc = gt["expected_page_count"]
        assert actual_pc == expected_pc, f"page_count: expected {expected_pc}, got {actual_pc}"

    if "expected_text_length_range" in gt:
        lo, hi = gt["expected_text_length_range"]
        actual_len = len(result.markdown)
        assert lo <= actual_len <= hi, f"markdown length {actual_len} not in [{lo}, {hi}]"

    if "expected_table_count" in gt:
        actual_tc = len(result.tables)
        expected_tc = gt["expected_table_count"]
        assert actual_tc == expected_tc, f"table count: expected {expected_tc}, got {actual_tc}"

    if "expected_image_count" in gt:
        actual_ic = len(result.images)
        expected_ic = gt["expected_image_count"]
        assert actual_ic == expected_ic, f"image count: expected {expected_ic}, got {actual_ic}"

    if "expected_sections" in gt:
        missing = [s for s in gt["expected_sections"] if s not in result.markdown]
        assert not missing, f"missing sections in markdown: {missing}"

    if "expected_keywords" in gt:
        missing_kw = [k for k in gt["expected_keywords"] if k not in result.markdown]
        assert not missing_kw, f"missing keywords in markdown: {missing_kw}"

    if "expected_title" in gt:
        actual_title = result.metadata.title
        expected_title = gt["expected_title"]
        assert actual_title == expected_title, (
            f"title: expected {expected_title!r}, got {actual_title!r}"
        )
