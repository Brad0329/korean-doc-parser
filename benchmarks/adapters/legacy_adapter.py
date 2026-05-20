"""Adapter for the lets_portal legacy file_parser.py — our baseline.

The legacy parser lives outside this repo. We import it by appending its
parent directory to sys.path. Override the location with the environment
variable LEGACY_FILE_PARSER (path to file_parser.py).
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
from pathlib import Path

from .base import BaseAdapter, ParseOutput

DEFAULT_LEGACY_PATH = Path(r"C:\Users\user\Documents\lets_portal\backend\utils\file_parser.py")


class LegacyFileParserAdapter(BaseAdapter):
    name = "legacy_file_parser"

    def __init__(self) -> None:
        self._module = None
        location = Path(os.environ.get("LEGACY_FILE_PARSER", DEFAULT_LEGACY_PATH))
        if not location.is_file():
            return
        parent = str(location.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        try:
            spec = importlib.util.spec_from_file_location("legacy_file_parser", location)
            if spec is None or spec.loader is None:
                return
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._module = module
        except Exception:
            self._module = None

    def is_available(self) -> bool:
        return self._module is not None

    def supported_formats(self) -> set[str]:
        return {".pdf", ".docx", ".hwpx", ".hwp", ".pptx"}

    def parse(self, path: Path) -> ParseOutput:
        if self._module is None:
            return ParseOutput(error="legacy file_parser.py not found (set LEGACY_FILE_PARSER)")

        extract = getattr(self._module, "extract_text", None) or getattr(
            self._module, "parse_file", None
        )
        if extract is None:
            return ParseOutput(error="extract_text() not found in legacy file_parser")

        result = extract(str(path))
        text, table_count, image_count = _normalize_legacy_result(result)
        return ParseOutput(
            text=text,
            table_count=table_count,
            image_count=image_count,
        )


def _normalize_legacy_result(result) -> tuple[str, int, int]:
    """legacy returns either ParseResult dataclass or a plain str — handle both."""
    if isinstance(result, str):
        text = result
        return text, _count_md_tables(text), _count_md_images(text)

    text = getattr(result, "text", None) or getattr(result, "content", None) or str(result)
    tables = getattr(result, "tables", None)
    images = getattr(result, "images", None)
    table_count = len(tables) if tables is not None else _count_md_tables(text)
    image_count = len(images) if images is not None else _count_md_images(text)
    return text, table_count, image_count


def _count_md_tables(md: str) -> int:
    return len(re.findall(r"^\s*\|?\s*:?-{3,}\s*(\|\s*:?-{3,}\s*)+\|?\s*$", md, re.MULTILINE))


def _count_md_images(md: str) -> int:
    return len(re.findall(r"!\[[^\]]*\]\([^)]+\)", md))
