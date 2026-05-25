"""korean-doc-parser-hwp — HWP (Hangul Word Processor) parser extras.

This package is AGPL-3.0-or-later licensed because it depends on pyhwp (AGPLv3+).
It registers an HwpParser with the core registry on import — ``import
korean_doc_parser_hwp`` is enough; downstream callers can keep using
``korean_doc_parser.extract(path)``.
"""

from korean_doc_parser_hwp.parser import HwpParser

__version__ = "1.0.0"

__all__ = [
    "HwpParser",
    "__version__",
]
