"""PPTX parser — delegates to markitdown (Phase 0 decision).

Phase 0 benchmark (worklog/001) put markitdown at 23K text vs 170 for a
hand-rolled python-pptx parser. v0.3 ships the delegation; v0.3 N>=5
evaluation (worklog/010) is what makes the delegation final.

Heavy optional dependency: ``markitdown[pptx]`` pulls in ``onnxruntime`` +
``numpy`` + ``magika`` (~80MB). Therefore this parser is **opt-in only** —
``pip install korean-doc-parser[pptx]``. When markitdown isn't installed,
this module imports cleanly but doesn't register itself with the registry,
so a core-only install gets a friendly :class:`UnsupportedFormatError`
instead of an ``ImportError``.

The parser registers itself with the global registry on import **iff**
markitdown is importable.
"""

from __future__ import annotations

from pathlib import Path

from korean_doc_parser.core import (
    BaseParser,
    ParseMetadata,
    ParseResult,
    register_parser,
)
from korean_doc_parser.exceptions import ParseError

__all__ = ["PptxParser"]


class PptxParser(BaseParser):
    """Parse ``.pptx`` files via markitdown.

    v0.3 contract:
    * ``markdown`` — markitdown's slide-by-slide output (``<!-- Slide number: N -->``
      delimiters preserved)
    * ``tables`` — empty in v0.3. markitdown emits tables as markdown text inline
      with paragraphs; promoting them to ``ParsedTable`` requires re-parsing the
      markdown which loses fidelity. Deferred to v0.4+.
    * ``images`` — empty in v0.3. markitdown emits ``![](filename)`` placeholders
      without the bitmap bytes. Bitmap extraction would need python-pptx direct
      access. Deferred.
    * ``metadata.title`` — best-effort from python-pptx ``core_properties``.
    """

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        return (".pptx",)

    def parse(self, path: Path) -> ParseResult:
        from markitdown import MarkItDown

        try:
            md = MarkItDown()
            result = md.convert(str(path))
            markdown = result.text_content or ""

            metadata = ParseMetadata(
                format="pptx",
                file_path=path,
                title=_extract_title(path),
            )

            return ParseResult(
                markdown=markdown,
                metadata=metadata,
                tables=[],
                images=[],
            )
        except ParseError:
            raise
        except Exception as exc:
            msg = f"Failed to parse PPTX {path}: {exc}"
            raise ParseError(msg) from exc


def _extract_title(path: Path) -> str | None:
    """Best-effort title from PPTX core properties.

    Returns ``None`` on any failure — title is informational, not contractual.
    python-pptx is pulled in by ``markitdown[pptx]`` extras so importing it is
    safe inside the gated branch.
    """
    try:
        from pptx import Presentation

        prs = Presentation(str(path))
        title = prs.core_properties.title
        return title or None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Conditional auto-register — only when markitdown is available
# ─────────────────────────────────────────────────────────────────────────────

try:
    import markitdown  # noqa: F401

    register_parser(PptxParser())
except ImportError:
    # Core-only install — .pptx will raise UnsupportedFormatError, which is
    # the documented behaviour. Hint the user in the message at the caller.
    pass
