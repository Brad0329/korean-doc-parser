"""Adapter registry for benchmark targets.

Each adapter wraps one library. Adapters whose import fails (library not
installed) report is_available() == False and the runner skips them gracefully.
"""

from __future__ import annotations

from .base import BaseAdapter, ParseOutput
from .docling_adapter import DoclingAdapter
from .legacy_adapter import LegacyFileParserAdapter
from .marker_adapter import MarkerAdapter
from .markitdown_adapter import MarkitdownAdapter
from .unstructured_adapter import UnstructuredAdapter

ALL_ADAPTERS: list[type[BaseAdapter]] = [
    MarkitdownAdapter,
    MarkerAdapter,
    DoclingAdapter,
    UnstructuredAdapter,
    LegacyFileParserAdapter,
]

__all__ = [
    "ALL_ADAPTERS",
    "BaseAdapter",
    "ParseOutput",
    "MarkitdownAdapter",
    "MarkerAdapter",
    "DoclingAdapter",
    "UnstructuredAdapter",
    "LegacyFileParserAdapter",
]
