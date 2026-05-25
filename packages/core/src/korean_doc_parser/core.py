"""Core public types and parser registry for korean-doc-parser.

This module defines the stable contract every per-format parser must satisfy:

* :class:`ParseResult` — the engine's output (markdown, tables, images, metadata)
* :class:`ExtractedImage` — one image with positional/contextual metadata
* :class:`ParsedTable` — one table with optional caption + page locator
* :class:`ParseMetadata` — document-level metadata
* :class:`BaseParser` — abstract base class every parser implements
* :class:`ParserRegistry` — extension → parser mapping (plugin pattern)
* :func:`extract` — top-level entry point used by callers

External packages (``korean-doc-parser-hwp``) register their parsers with the
global registry via :func:`register_parser`. The core package is unaware of
those extras (dependency-inversion — see CLAUDE.md §"패키지 경계").
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from korean_doc_parser.exceptions import UnsupportedFormatError

BboxUnit = Literal["px", "emu", "none"]
"""Unit of an :class:`ExtractedImage` bbox (v0.5.0, worklog/019 § 3-4).

* ``"px"`` — pixels (PDF, native pdfplumber units)
* ``"emu"`` — English Metric Unit (PPTX, 1 inch = 914400 EMU)
* ``"none"`` — no bbox (HWP / HWPX / DOCX parsers)

Future formats can add to this Literal as new bbox sources land. Downstream
proximity / dedup logic uses this to decide whether two bboxes are
comparable in the same numeric space.
"""

__all__ = [
    "BaseParser",
    "BboxUnit",
    "ExtractedImage",
    "ParseMetadata",
    "ParseResult",
    "ParsedTable",
    "ParserRegistry",
    "extract",
    "get_parser",
    "register_parser",
    "supported_extensions",
]


# ─────────────────────────────────────────────────────────────────────────────
# Result data types
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ParsedTable:
    """One table extracted from a document.

    ``rows`` is a list of row cells, top-to-bottom, left-to-right.
    Cells are plain strings. Empty cells are represented as ``""`` (never
    ``None``) so that downstream consumers can iterate without isinstance checks.
    """

    rows: list[list[str]]
    page_no: int | None = None
    caption: str | None = None
    order_in_page: int = 0


@dataclass(frozen=True, slots=True)
class ExtractedImage:
    """One image extracted from a document, with the metadata bundle defined
    in HANDOVER §2-7.

    Positional fields are populated when applicable (e.g. ``bbox`` only for
    PDF). Engine-stage fields (sha256, caption regex hit) are filled by the
    parser; pipeline-stage fields (AI caption, confidence) live on a separate
    type in the ``korean-doc-parser-pipeline`` package.
    """

    # === position ===
    page_no: int | None
    section_no: int | None
    bbox: tuple[float, float, float, float] | None
    bbox_unit: BboxUnit
    """Unit of ``bbox`` coordinates (v0.5.0, worklog/019 § 3-4).

    * ``"px"`` — PDF (pdfplumber native pixels at the document's render DPI)
    * ``"emu"`` — PPTX (English Metric Unit, 1 inch = 914400 EMU)
    * ``"none"`` — bbox unavailable (HWP / HWPX / DOCX in current parsers).
      When ``bbox is None`` this field must also be ``"none"``.

    Downstream callers using ``pipeline.detect_caption_proximity`` must keep
    image and text bboxes in the same unit per call — comparing px against
    EMU produces meaningless distances.
    """
    order_in_page: int

    # === surrounding text context ===
    text_before: str
    text_after: str
    section_title: str | None

    # === file ===
    file_path: str
    sha256: str
    width: int
    height: int
    size_bytes: int
    mime_type: str

    # === first-pass caption detection (deterministic, engine-side) ===
    detected_caption: str | None
    caption_method: str | None  # "regex" | "proximity" | None
    caption_pattern_score: float  # 0.0 - 1.0


@dataclass(frozen=True, slots=True)
class ParseMetadata:
    """Document-level metadata. All fields optional except ``format`` and
    ``file_path`` which are guaranteed to be filled.
    """

    format: str  # e.g. "pdf", "hwp", "hwpx" — lowercase, no leading dot
    file_path: Path
    page_count: int | None = None
    title: str | None = None
    author: str | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    extra: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ParseResult:
    """Engine output. The single object returned by :func:`extract`."""

    markdown: str
    metadata: ParseMetadata
    tables: list[ParsedTable] = field(default_factory=list)
    images: list[ExtractedImage] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Parser ABC + registry
# ─────────────────────────────────────────────────────────────────────────────


class BaseParser(ABC):
    """Abstract base class every per-format parser implements.

    Implementations live in :mod:`korean_doc_parser.parsers` (built-in) and
    in external packages such as ``korean-doc-parser-hwp`` that register
    themselves via :func:`register_parser` on import.
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> tuple[str, ...]:
        """Lowercase, leading-dot file extensions this parser handles.

        Example: ``(".pdf",)`` or ``(".doc",)``.
        """

    @abstractmethod
    def parse(self, path: Path) -> ParseResult:
        """Parse ``path`` and return a :class:`ParseResult`.

        Implementations may raise :class:`ParseError` (or a subclass) for
        recoverable failures, and ``FileNotFoundError`` if ``path`` vanished
        between the caller's check and the parser's read.
        """


class ParserRegistry:
    """Maps file extensions to :class:`BaseParser` instances.

    A single global instance is shared across the process — see
    :data:`_GLOBAL_REGISTRY`. External packages register their parsers by
    calling :func:`register_parser` at import time.
    """

    def __init__(self) -> None:
        self._parsers: dict[str, BaseParser] = {}

    def register(self, parser: BaseParser) -> None:
        """Register ``parser`` under each of its supported extensions.

        If an extension is already registered, the new parser replaces the
        previous one (last-write-wins). This allows extras packages to
        override built-in fallbacks.
        """
        for ext in parser.supported_extensions:
            self._parsers[ext.lower()] = parser

    def get(self, extension: str) -> BaseParser | None:
        """Look up a parser by extension. Case-insensitive."""
        return self._parsers.get(extension.lower())

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        """All currently-registered extensions, sorted, lowercase."""
        return tuple(sorted(self._parsers.keys()))


_GLOBAL_REGISTRY = ParserRegistry()


def register_parser(parser: BaseParser) -> None:
    """Register ``parser`` in the global process-wide registry."""
    _GLOBAL_REGISTRY.register(parser)


def get_parser(extension: str) -> BaseParser | None:
    """Look up a parser by file extension in the global registry."""
    return _GLOBAL_REGISTRY.get(extension)


def supported_extensions() -> tuple[str, ...]:
    """Snapshot of all extensions currently handled by the global registry."""
    return _GLOBAL_REGISTRY.supported_extensions


# ─────────────────────────────────────────────────────────────────────────────
# Top-level entry point
# ─────────────────────────────────────────────────────────────────────────────


def extract(path: str | Path) -> ParseResult:
    """Parse ``path`` using the registered parser for its extension.

    Raises
    ------
    FileNotFoundError
        ``path`` does not exist or is not a regular file.
    UnsupportedFormatError
        No parser is registered for ``path``'s extension. The error message
        lists the currently-supported extensions for diagnostic purposes.
    ParseError
        The registered parser failed; cause chained via ``__cause__``.
    """
    p = Path(path)
    if not p.is_file():
        msg = f"Not a regular file: {p}"
        raise FileNotFoundError(msg)

    parser = _GLOBAL_REGISTRY.get(p.suffix)
    if parser is None:
        supported = _GLOBAL_REGISTRY.supported_extensions
        msg = f"No parser registered for extension {p.suffix!r}. Currently supported: {supported}"
        raise UnsupportedFormatError(msg)

    return parser.parse(p)
