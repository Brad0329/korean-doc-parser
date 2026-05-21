"""Synthetic fixture generators — code-built tiny documents for tests.

Each generator returns a ``Path`` to a freshly-built file inside the caller-
provided directory. Generators stay format-isolated so a missing optional dep
(e.g. ``python-docx``) only breaks the formats that need it.

Used by :mod:`conftest` session-scoped pytest fixtures so the cost is paid
once per test run.

Ground-truth JSON is written next to the fixture so per-parser tests can call
:func:`korean_doc_parser.tests._gt.load_ground_truth` uniformly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__all__ = [
    "build_docx_simple",
    "build_docx_with_table",
    "build_hwpx_simple",
]


def _write_gt(fixture_path: Path, gt: dict[str, Any]) -> None:
    """Persist ground truth JSON alongside ``fixture_path``."""
    gt_path = fixture_path.with_name(fixture_path.name + ".gt.json")
    gt_path.write_text(
        json.dumps(gt, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


# ─────────────────────────────────────────────────────────────────────────────
# DOCX
# ─────────────────────────────────────────────────────────────────────────────


def build_docx_simple(dest_dir: Path) -> Path:
    """Build a 1-paragraph DOCX with a heading. Returns the fixture path."""
    from docx import Document

    path = dest_dir / "docx_simple.docx"
    doc = Document()
    doc.add_heading("테스트 문서 제목", level=1)
    doc.add_paragraph(
        "이것은 합성 테스트용 한국어 DOCX 문서입니다. "
        "본문 길이를 검증하기 위한 충분한 길이의 텍스트를 포함합니다."
    )
    doc.save(str(path))

    _write_gt(
        path,
        {
            "expected_format": "docx",
            "expected_table_count": 0,
            "expected_image_count": 0,
            "expected_sections": ["테스트 문서 제목"],
            "expected_keywords": ["합성 테스트용", "한국어 DOCX"],
            "expected_text_length_range": [40, 500],
        },
    )
    return path


def build_docx_with_table(dest_dir: Path) -> Path:
    """Build a DOCX containing a single 3-by-3 table. Returns the fixture path."""
    from docx import Document

    path = dest_dir / "docx_with_table.docx"
    doc = Document()
    doc.add_heading("표 포함 문서", level=1)
    doc.add_paragraph("아래 표는 예시 데이터입니다.")

    table = doc.add_table(rows=3, cols=3)
    headers = ["항목", "값", "비고"]
    for i, h in enumerate(headers):
        table.rows[0].cells[i].text = h
    table.rows[1].cells[0].text = "매출"
    table.rows[1].cells[1].text = "1,000"
    table.rows[1].cells[2].text = "단위: 백만 원"
    table.rows[2].cells[0].text = "비용"
    table.rows[2].cells[1].text = "600"
    table.rows[2].cells[2].text = "고정비 포함"

    doc.save(str(path))

    _write_gt(
        path,
        {
            "expected_format": "docx",
            "expected_table_count": 1,
            "expected_image_count": 0,
            "expected_sections": ["표 포함 문서"],
            "expected_keywords": ["항목", "매출", "비용"],
            "expected_text_length_range": [30, 500],
        },
    )
    return path


# ─────────────────────────────────────────────────────────────────────────────
# HWPX — direct OOXML-style XML (no external dependency)
# ─────────────────────────────────────────────────────────────────────────────

_HWPX_MIMETYPE = "application/hwp+zip"

_HWPX_CONTENT_HPF = """<?xml version="1.0" encoding="UTF-8"?>
<opf:package xmlns:opf="http://www.idpf.org/2007/opf">
  <opf:metadata>
    <opf:title>HWPX 합성 픽스처</opf:title>
  </opf:metadata>
</opf:package>
"""

_HWPX_SECTION0_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:p>
    <hp:run><hp:t>HWPX 합성 픽스처</hp:t></hp:run>
  </hp:p>
  <hp:p>
    <hp:run><hp:t>이것은 코드로 생성한 최소 HWPX 본문입니다.</hp:t></hp:run>
  </hp:p>
</hp:sec>
"""


def build_hwpx_simple(dest_dir: Path) -> Path:
    """Build a minimal valid HWPX (ZIP with mimetype + content + section).

    The XML is intentionally simple so the parser test focuses on structure
    handling, not Hancom's full schema. Real HWPX from 한/글 has much richer
    namespacing; the parser must tolerate this minimal shape too.
    """
    import zipfile

    path = dest_dir / "hwpx_simple.hwpx"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # mimetype must be stored (not deflated) and first per the OPF spec;
        # for synthetic-test purposes we don't enforce STORED here.
        zf.writestr("mimetype", _HWPX_MIMETYPE)
        zf.writestr("Contents/content.hpf", _HWPX_CONTENT_HPF)
        zf.writestr("Contents/section0.xml", _HWPX_SECTION0_XML)

    _write_gt(
        path,
        {
            "expected_format": "hwpx",
            "expected_table_count": 0,
            "expected_image_count": 0,
            "expected_sections": ["HWPX 합성 픽스처"],
            "expected_keywords": ["코드로 생성한 최소 HWPX"],
            "expected_text_length_range": [20, 500],
        },
    )
    return path
