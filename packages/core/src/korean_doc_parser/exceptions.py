"""Exception hierarchy for korean-doc-parser.

All library-raised errors inherit from :class:`KoreanDocParserError` so callers
can catch the whole library with a single ``except`` clause.
"""

from __future__ import annotations

__all__ = [
    "KoreanDocParserError",
    "ParseError",
    "UnsupportedFormatError",
]


class KoreanDocParserError(Exception):
    """Base class for all korean-doc-parser errors."""


class UnsupportedFormatError(KoreanDocParserError):
    """Raised when no parser is registered for the file's extension."""


class ParseError(KoreanDocParserError):
    """Raised when a registered parser fails during extraction.

    The underlying cause (if any) is preserved via ``raise … from``.
    """
