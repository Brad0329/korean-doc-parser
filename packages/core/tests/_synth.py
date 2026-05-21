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
    "build_docx_with_image",
    "build_docx_with_table",
    "build_hwpx_simple",
    "build_hwpx_with_table",
    "build_pdf_multipage",
    "build_pdf_simple",
    "build_pdf_with_image",
    "build_pdf_with_table",
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
            # Note: table cells live in result.tables (not in markdown),
            # so the keyword check targets paragraph body only.
            "expected_keywords": ["예시 데이터"],
            "expected_text_length_range": [20, 500],
        },
    )
    return path


def build_docx_with_image(dest_dir: Path) -> Path:
    """Synthetic DOCX containing one inline image (32-by-32 PNG)."""
    from io import BytesIO

    from docx import Document
    from PIL import Image

    path = dest_dir / "docx_with_image.docx"
    doc = Document()
    doc.add_heading("이미지 포함 문서", level=1)
    doc.add_paragraph("아래 그림은 임베디드 이미지입니다.")

    png_buf = BytesIO()
    Image.new("RGB", (32, 32), (0, 128, 0)).save(png_buf, format="PNG")
    png_buf.seek(0)
    doc.add_picture(png_buf, width=None)
    doc.save(str(path))

    _write_gt(
        path,
        {
            "expected_format": "docx",
            "expected_table_count": 0,
            "expected_image_count": 1,
            "expected_sections": ["이미지 포함 문서"],
            "expected_keywords": ["임베디드 이미지"],
            "expected_text_length_range": [10, 500],
        },
    )
    return path


# ─────────────────────────────────────────────────────────────────────────────
# PDF — reportlab. English text only (default fonts lack Korean glyphs);
# Korean PDF coverage comes from real `samples/*.pdf` fixtures, not synth.
# ─────────────────────────────────────────────────────────────────────────────


def build_pdf_simple(dest_dir: Path) -> Path:
    """Synthetic single-page PDF with English text."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    path = dest_dir / "pdf_simple.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle("Synthetic PDF Title")
    c.setAuthor("doc_parser tests")
    c.drawString(72, 800, "Synthetic PDF Fixture")
    c.drawString(72, 770, "This is a minimal one-page PDF for parser tests.")
    c.showPage()
    c.save()

    _write_gt(
        path,
        {
            "expected_format": "pdf",
            "expected_page_count": 1,
            "expected_table_count": 0,
            "expected_image_count": 0,
            "expected_sections": ["Synthetic PDF Fixture"],
            "expected_keywords": ["minimal one-page PDF"],
            "expected_text_length_range": [30, 500],
            "expected_title": "Synthetic PDF Title",
        },
    )
    return path


def build_pdf_multipage(dest_dir: Path) -> Path:
    """Synthetic 3-page PDF — exercises page_count + multi-page text join."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    path = dest_dir / "pdf_multipage.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    for i in range(3):
        c.drawString(72, 800, f"Page {i + 1} of 3")
        c.drawString(72, 770, f"Content on page {i + 1}.")
        c.showPage()
    c.save()

    _write_gt(
        path,
        {
            "expected_format": "pdf",
            "expected_page_count": 3,
            "expected_table_count": 0,
            "expected_image_count": 0,
            "expected_sections": ["Page 1 of 3", "Page 2 of 3", "Page 3 of 3"],
            "expected_text_length_range": [40, 500],
        },
    )
    return path


def build_pdf_with_table(dest_dir: Path) -> Path:
    """Synthetic single-page PDF with one 3-by-3 table."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table

    path = dest_dir / "pdf_with_table.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("PDF with Table Fixture", styles["Heading1"]),
        Spacer(1, 12),
        Table(
            [
                ["Item", "Value", "Note"],
                ["Revenue", "1000", "Unit: million KRW"],
                ["Cost", "600", "Includes fixed cost"],
            ],
            style=[
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ],
        ),
    ]
    doc.build(story)

    _write_gt(
        path,
        {
            "expected_format": "pdf",
            "expected_page_count": 1,
            "expected_table_count": 1,
            "expected_image_count": 0,
            "expected_sections": ["PDF with Table Fixture"],
            "expected_keywords": ["Revenue", "Cost"],
            "expected_text_length_range": [50, 1500],
        },
    )
    return path


def build_pdf_with_image(dest_dir: Path) -> Path:
    """Synthetic single-page PDF embedding a 32-by-32 red square PNG."""
    from io import BytesIO

    from PIL import Image
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    path = dest_dir / "pdf_with_image.pdf"

    png_buf = BytesIO()
    Image.new("RGB", (32, 32), (255, 0, 0)).save(png_buf, format="PNG")
    png_buf.seek(0)

    c = canvas.Canvas(str(path), pagesize=A4)
    c.drawString(72, 800, "PDF with Image Fixture")
    c.drawImage(ImageReader(png_buf), 100, 700, width=32, height=32)
    c.showPage()
    c.save()

    _write_gt(
        path,
        {
            "expected_format": "pdf",
            "expected_page_count": 1,
            "expected_table_count": 0,
            "expected_image_count": 1,
            "expected_sections": ["PDF with Image Fixture"],
            "expected_text_length_range": [10, 500],
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


_HWPX_SECTION0_TABLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">
  <hp:p>
    <hp:run><hp:t>표 포함 HWPX</hp:t></hp:run>
  </hp:p>
  <hp:p>
    <hp:tbl>
      <hp:tr>
        <hp:tc><hp:run><hp:t>A</hp:t></hp:run></hp:tc>
        <hp:tc><hp:run><hp:t>B</hp:t></hp:run></hp:tc>
      </hp:tr>
      <hp:tr>
        <hp:tc><hp:run><hp:t>1</hp:t></hp:run></hp:tc>
        <hp:tc><hp:run><hp:t>2</hp:t></hp:run></hp:tc>
      </hp:tr>
    </hp:tbl>
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
            "expected_title": "HWPX 합성 픽스처",
        },
    )
    return path


def build_hwpx_with_table(dest_dir: Path) -> Path:
    """Build a minimal HWPX containing one 2-by-2 table inside section0."""
    import zipfile

    path = dest_dir / "hwpx_with_table.hwpx"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", _HWPX_MIMETYPE)
        zf.writestr("Contents/content.hpf", _HWPX_CONTENT_HPF)
        zf.writestr("Contents/section0.xml", _HWPX_SECTION0_TABLE_XML)

    _write_gt(
        path,
        {
            "expected_format": "hwpx",
            "expected_table_count": 1,
            "expected_image_count": 0,
            "expected_sections": ["표 포함 HWPX"],
            "expected_text_length_range": [5, 200],
        },
    )
    return path
