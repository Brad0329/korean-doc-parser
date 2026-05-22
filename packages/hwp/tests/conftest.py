"""HWP package fixtures.

Real HWP fixtures live in ``<repo>/samples/*.hwp`` and are NOT committed to
git (private inputs — only the per-file ``*.gt.json`` ground truth is shared).
Each fixture skips when its source file is absent so a fresh clone (or CI
without secrets) can still run the rest of the suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SAMPLES_DIR = _REPO_ROOT / "samples"


def _hwp_or_skip(name: str) -> Path:
    """Return ``samples/<name>``, or ``pytest.skip`` if it's missing."""
    p = _SAMPLES_DIR / name
    if not p.is_file():
        pytest.skip(f"HWP fixture missing: {p}")
    return p


@pytest.fixture(scope="session")
def hwp_test_nara() -> Path:
    """Small (~228 KB) public-domain-ish proposal — quickest regression target."""
    return _hwp_or_skip("test_nara.hwp")


@pytest.fixture(scope="session")
def hwp_wku() -> Path:
    return _hwp_or_skip("proposal_wku.hwp")


@pytest.fixture(scope="session")
def hwp_gyeongnam_fishery() -> Path:
    return _hwp_or_skip("proposal_gyeongnam_fishery.hwp")


@pytest.fixture(scope="session")
def hwp_forest_startup() -> Path:
    """Largest fixture (~22 MB binary, 36 KB markdown) — exercises long-doc path."""
    return _hwp_or_skip("proposal_forest_startup.hwp")


@pytest.fixture(scope="session")
def hwp_proposal_consulting() -> Path:
    """Pre-existing fixture from before v0.2 (had legacy GT format, updated)."""
    return _hwp_or_skip("3. 정성적 제안서_창업역량강화교육프로그램운영용역_(주)렛츠_231030-02.hwp")
