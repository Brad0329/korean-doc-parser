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
    "hwpx_with_table",
    "pdf_multipage",
    "pdf_simple",
    "pdf_with_image",
    "pdf_with_table",
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
