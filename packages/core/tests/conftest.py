"""Shared pytest fixtures for the core package.

Session-scoped synthetic fixtures live here so each test run pays the build
cost once. Per-format generators are defined in :mod:`_synth`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests import _synth

__all__ = [
    "docx_simple",
    "docx_with_image",
    "docx_with_table",
    "fixtures_dir",
    "hwpx_simple",
    "hwpx_with_image",
    "hwpx_with_image_corrupt",
    "hwpx_with_image_resources",
    "hwpx_with_table",
    "pdf_multipage",
    "pdf_simple",
    "pdf_with_image",
    "pdf_with_image_cmyk",
    "pdf_with_image_jpeg",
    "pdf_with_multi_images",
    "pdf_with_table",
    "pptx_letsportal_tmp",
    "pptx_multislide",
    "pptx_qvan_storyboard",
    "pptx_simple",
    "pptx_tour_corp",
    "pptx_vanasso_corrupt",
    "pptx_with_image",
    "pptx_with_table",
]


@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A session-scoped temp directory holding synthetic fixtures."""
    return tmp_path_factory.mktemp("synth_fixtures")


@pytest.fixture(scope="session")
def docx_simple(fixtures_dir: Path) -> Path:
    return _synth.build_docx_simple(fixtures_dir)


@pytest.fixture(scope="session")
def docx_with_table(fixtures_dir: Path) -> Path:
    return _synth.build_docx_with_table(fixtures_dir)


@pytest.fixture(scope="session")
def docx_with_image(fixtures_dir: Path) -> Path:
    return _synth.build_docx_with_image(fixtures_dir)


@pytest.fixture(scope="session")
def hwpx_simple(fixtures_dir: Path) -> Path:
    return _synth.build_hwpx_simple(fixtures_dir)


@pytest.fixture(scope="session")
def hwpx_with_table(fixtures_dir: Path) -> Path:
    return _synth.build_hwpx_with_table(fixtures_dir)


@pytest.fixture(scope="session")
def hwpx_with_image(fixtures_dir: Path) -> Path:
    return _synth.build_hwpx_with_image(fixtures_dir)


@pytest.fixture(scope="session")
def hwpx_with_image_resources(fixtures_dir: Path) -> Path:
    return _synth.build_hwpx_with_image_resources(fixtures_dir)


@pytest.fixture(scope="session")
def hwpx_with_image_corrupt(fixtures_dir: Path) -> Path:
    return _synth.build_hwpx_with_image_corrupt(fixtures_dir)


@pytest.fixture(scope="session")
def pdf_simple(fixtures_dir: Path) -> Path:
    return _synth.build_pdf_simple(fixtures_dir)


@pytest.fixture(scope="session")
def pdf_multipage(fixtures_dir: Path) -> Path:
    return _synth.build_pdf_multipage(fixtures_dir)


@pytest.fixture(scope="session")
def pdf_with_table(fixtures_dir: Path) -> Path:
    return _synth.build_pdf_with_table(fixtures_dir)


@pytest.fixture(scope="session")
def pdf_with_image(fixtures_dir: Path) -> Path:
    return _synth.build_pdf_with_image(fixtures_dir)


@pytest.fixture(scope="session")
def pdf_with_image_jpeg(fixtures_dir: Path) -> Path:
    return _synth.build_pdf_with_image_jpeg(fixtures_dir)


@pytest.fixture(scope="session")
def pdf_with_image_cmyk(fixtures_dir: Path) -> Path:
    return _synth.build_pdf_with_image_cmyk(fixtures_dir)


@pytest.fixture(scope="session")
def pdf_with_multi_images(fixtures_dir: Path) -> Path:
    return _synth.build_pdf_with_multi_images(fixtures_dir)


# ─── PPTX synthetic fixtures (v0.3) ──────────────────────────────────────────


@pytest.fixture(scope="session")
def pptx_simple(fixtures_dir: Path) -> Path:
    return _synth.build_pptx_simple(fixtures_dir)


@pytest.fixture(scope="session")
def pptx_multislide(fixtures_dir: Path) -> Path:
    return _synth.build_pptx_multislide(fixtures_dir)


@pytest.fixture(scope="session")
def pptx_with_table(fixtures_dir: Path) -> Path:
    return _synth.build_pptx_with_table(fixtures_dir)


@pytest.fixture(scope="session")
def pptx_with_image(fixtures_dir: Path) -> Path:
    return _synth.build_pptx_with_image(fixtures_dir)


# ─── PPTX real-world fixtures (v0.3, samples/ — skip-guarded) ───────────────

_REPO_ROOT_FOR_SAMPLES = Path(__file__).resolve().parents[3]
_SAMPLES_DIR = _REPO_ROOT_FOR_SAMPLES / "samples"


def _pptx_or_skip(name: str) -> Path:
    p = _SAMPLES_DIR / name
    if not p.is_file():
        pytest.skip(f"PPTX fixture missing: {p}")
    return p


@pytest.fixture(scope="session")
def pptx_tour_corp() -> Path:
    """37-slide proposal — moderate size baseline (~23K markdown)."""
    return _pptx_or_skip(
        "●제안서(최종)_한국관광공사_성장 관광벤처기업 교육 컨설팅_(주)렛츠_20210509-2.pptx"
    )


@pytest.fixture(scope="session")
def pptx_letsportal_tmp() -> Path:
    """42-slide PPTX — exercises mid-size markitdown output (~38K markdown)."""
    return _pptx_or_skip("pptx_letsportal_tmp.pptx")


@pytest.fixture(scope="session")
def pptx_qvan_storyboard() -> Path:
    """142-slide storyboard — largest fixture, ~113K markdown / 2.5s parse."""
    return _pptx_or_skip("pptx_qvan_storyboard.pptx")


@pytest.fixture(scope="session")
def pptx_vanasso_corrupt() -> Path:
    """204-byte corrupted PPTX — proves ParseError is raised, service survives."""
    return _pptx_or_skip("pptx_vanasso_upload1.pptx")
