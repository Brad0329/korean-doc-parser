"""korean-doc-parser — HWP-aware document-to-markdown library for Korean documents.

This module re-exports the stable public API. Anything not listed in
``__all__`` is considered internal and may change without a SemVer bump.

SemVer (CLAUDE.md §"라이브러리 특화 규칙 §1"):
* patch — bug fixes only
* minor — backward-compatible additions to this surface
* major — backward-incompatible changes
"""

from __future__ import annotations

from korean_doc_parser.core import (
    BaseParser,
    ExtractedImage,
    ParsedTable,
    ParseMetadata,
    ParseResult,
    ParserRegistry,
    extract,
    get_parser,
    register_parser,
    supported_extensions,
)
from korean_doc_parser.exceptions import (
    KoreanDocParserError,
    ParseError,
    UnsupportedFormatError,
)

# Side-effect imports: each built-in parser registers itself with the global
# registry on import. Extras packages (e.g. korean-doc-parser-hwp) do the same
# on their own import.
from korean_doc_parser.parsers import docx as _docx
from korean_doc_parser.parsers import hwpx as _hwpx
from korean_doc_parser.parsers import pdf as _pdf
from korean_doc_parser.parsers import pptx as _pptx

__version__ = "0.3.0"

__all__ = [
    "BaseParser",
    "ExtractedImage",
    "KoreanDocParserError",
    "ParseError",
    "ParseMetadata",
    "ParseResult",
    "ParsedTable",
    "ParserRegistry",
    "UnsupportedFormatError",
    "__version__",
    "extract",
    "get_parser",
    "register_parser",
    "supported_extensions",
]
