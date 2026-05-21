"""Common adapter interface for benchmark targets.

Every parser library we evaluate is wrapped in a BaseAdapter subclass so that
compare.py can drive them through one uniform call. Adapters are responsible
for measuring their own wall-clock duration; peak memory is captured by the
runner outside of this module.
"""

from __future__ import annotations

import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParseOutput:
    """Normalized output every adapter must return."""

    text: str = ""
    table_count: int = 0
    image_count: int = 0
    duration_ms: float = 0.0
    peak_mem_mb: float = 0.0
    error: str | None = None
    raw_markdown: str | None = None
    extra: dict = field(default_factory=dict)


class BaseAdapter:
    """Wraps one parser library behind a uniform parse() call."""

    name: str = "base"

    def is_available(self) -> bool:
        """Whether the underlying library can be imported in this environment."""
        return False

    def supported_formats(self) -> set[str]:
        """Lowercase extensions including the dot, e.g. {'.pdf', '.docx'}."""
        return set()

    def parse(self, path: Path) -> ParseOutput:
        raise NotImplementedError

    def run(self, path: Path) -> ParseOutput:
        """Public entry — wraps parse() with timing and exception capture."""
        start = time.perf_counter()
        try:
            out = self.parse(path)
        except Exception as exc:
            return ParseOutput(
                error=f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=3)}",
                duration_ms=(time.perf_counter() - start) * 1000.0,
            )
        if out.duration_ms == 0.0:
            out.duration_ms = (time.perf_counter() - start) * 1000.0
        return out
