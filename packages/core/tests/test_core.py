"""Tests for the core public types and parser registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from korean_doc_parser import (
    BaseParser,
    ExtractedImage,
    ParsedTable,
    ParseError,
    ParseMetadata,
    ParseResult,
    ParserRegistry,
    UnsupportedFormatError,
    extract,
    get_parser,
    register_parser,
    supported_extensions,
)

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


class _StubParser(BaseParser):
    """Minimal parser used to exercise the registry + extract() entry point."""

    def __init__(self, extensions: tuple[str, ...], markdown: str = "ok") -> None:
        self._exts = extensions
        self._markdown = markdown
        self.calls: list[Path] = []

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        return self._exts

    def parse(self, path: Path) -> ParseResult:
        self.calls.append(path)
        return ParseResult(
            markdown=self._markdown,
            metadata=ParseMetadata(format=path.suffix.lstrip("."), file_path=path),
        )


@pytest.fixture
def tmp_pdf(tmp_path: Path) -> Path:
    p = tmp_path / "doc.pdf"
    p.write_bytes(b"%PDF-1.4\n%minimal\n")
    return p


# ─────────────────────────────────────────────────────────────────────────────
# Data types — basic invariants
# ─────────────────────────────────────────────────────────────────────────────


def test_parse_metadata_minimal_fields(tmp_path: Path) -> None:
    md = ParseMetadata(format="pdf", file_path=tmp_path / "x.pdf")
    assert md.format == "pdf"
    assert md.page_count is None
    assert md.extra == {}


def test_parse_result_defaults(tmp_path: Path) -> None:
    r = ParseResult(
        markdown="# title",
        metadata=ParseMetadata(format="hwp", file_path=tmp_path / "x.hwp"),
    )
    assert r.tables == []
    assert r.images == []


def test_parsed_table_shape() -> None:
    t = ParsedTable(rows=[["a", "b"], ["1", "2"]], page_no=3, caption="Table 1")
    assert t.rows[1][0] == "1"
    assert t.page_no == 3


def test_extracted_image_metadata_bundle() -> None:
    img = ExtractedImage(
        page_no=2,
        section_no=None,
        bbox=(0.0, 0.0, 100.0, 50.0),
        bbox_unit="px",
        order_in_page=0,
        text_before="앞 텍스트",
        text_after="뒷 텍스트",
        section_title="섹션 A",
        file_path="/tmp/img.png",
        sha256="deadbeef" * 8,
        width=100,
        height=50,
        size_bytes=1234,
        mime_type="image/png",
        detected_caption="[그림 1] 예시",
        caption_method="regex",
        caption_pattern_score=0.9,
    )
    assert img.bbox is not None
    assert img.caption_pattern_score == 0.9


def test_dataclasses_are_frozen(tmp_path: Path) -> None:
    md = ParseMetadata(format="pdf", file_path=tmp_path / "x.pdf")
    with pytest.raises((AttributeError, TypeError)):
        md.format = "docx"  # type: ignore[misc]


# ─────────────────────────────────────────────────────────────────────────────
# ParserRegistry (local instance) — isolation from the global registry
# ─────────────────────────────────────────────────────────────────────────────


def test_registry_register_and_get() -> None:
    reg = ParserRegistry()
    parser = _StubParser((".pdf",))
    reg.register(parser)

    assert reg.get(".pdf") is parser
    assert reg.get(".PDF") is parser  # case-insensitive
    assert reg.get(".docx") is None


def test_registry_supported_extensions_is_sorted_and_lowercase() -> None:
    reg = ParserRegistry()
    reg.register(_StubParser((".PDF", ".Hwp")))
    reg.register(_StubParser((".docx",)))
    assert reg.supported_extensions == (".docx", ".hwp", ".pdf")


def test_registry_last_write_wins() -> None:
    """Extras (e.g. hwp) may override built-ins by re-registering."""
    reg = ParserRegistry()
    first = _StubParser((".pdf",))
    second = _StubParser((".pdf",))
    reg.register(first)
    reg.register(second)
    assert reg.get(".pdf") is second


# ─────────────────────────────────────────────────────────────────────────────
# Global registry + extract() entry point
# ─────────────────────────────────────────────────────────────────────────────


def _restore_global_registry() -> dict[str, BaseParser]:
    """Snapshot the global registry so a test can mutate it and restore later.

    Returns the original ``_parsers`` mapping.
    """
    from korean_doc_parser import core as _core

    return dict(_core._GLOBAL_REGISTRY._parsers)


@pytest.fixture(autouse=True)
def _reset_global_registry() -> None:
    """Ensure each test sees a clean global registry."""
    from korean_doc_parser import core as _core

    snapshot = dict(_core._GLOBAL_REGISTRY._parsers)
    _core._GLOBAL_REGISTRY._parsers.clear()
    yield
    _core._GLOBAL_REGISTRY._parsers.clear()
    _core._GLOBAL_REGISTRY._parsers.update(snapshot)


def test_extract_routes_through_global_registry(tmp_pdf: Path) -> None:
    parser = _StubParser((".pdf",), markdown="# parsed")
    register_parser(parser)

    result = extract(tmp_pdf)

    assert result.markdown == "# parsed"
    assert result.metadata.format == "pdf"
    assert parser.calls == [tmp_pdf]


def test_extract_accepts_str_path(tmp_pdf: Path) -> None:
    register_parser(_StubParser((".pdf",)))
    result = extract(str(tmp_pdf))
    assert result.metadata.file_path == tmp_pdf


def test_extract_raises_file_not_found_for_missing_path(tmp_path: Path) -> None:
    register_parser(_StubParser((".pdf",)))
    with pytest.raises(FileNotFoundError):
        extract(tmp_path / "nope.pdf")


def test_extract_raises_unsupported_format_for_unknown_ext(tmp_path: Path) -> None:
    bogus = tmp_path / "x.unknown"
    bogus.write_text("data")
    with pytest.raises(UnsupportedFormatError, match=r"\.unknown"):
        extract(bogus)


def test_extract_propagates_parse_error(tmp_pdf: Path) -> None:
    class Failing(BaseParser):
        @property
        def supported_extensions(self) -> tuple[str, ...]:
            return (".pdf",)

        def parse(self, path: Path) -> ParseResult:
            msg = "simulated"
            raise ParseError(msg)

    register_parser(Failing())
    with pytest.raises(ParseError, match="simulated"):
        extract(tmp_pdf)


def test_get_parser_and_supported_extensions_helpers() -> None:
    assert get_parser(".pdf") is None
    parser = _StubParser((".pdf",))
    register_parser(parser)
    assert get_parser(".PDF") is parser
    assert ".pdf" in supported_extensions()
