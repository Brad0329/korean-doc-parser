"""SQLite-backed sha256+model cache for Vision labels (worklog/011 C.4).

v0.4 ships with SQLite because:
* Pipeline DB (PostgreSQL) is a v0.5 milestone — pulling it in for the CLI
  step would violate the worklog/011 § 8 milestone-split contract
* SQLite has no extra dependency (stdlib), so the [vision] extras stay tiny
* Cache rows are tiny (~1KB each) — file-based SQLite handles millions

v0.5 migration plan: keep the same row schema, swap the driver to asyncpg.
The CLI's --cache-path stays a usable escape hatch (e.g. shared NAS file).

Key = (sha256, model). When the model upgrades, old rows stay valid but
unused — new model creates fresh rows automatically.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS vision_cache (
    sha256 TEXT NOT NULL,
    model TEXT NOT NULL,
    caption TEXT NOT NULL,
    image_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    reasoning TEXT,
    cost_krw REAL NOT NULL,
    cost_usd REAL NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (sha256, model)
);
CREATE INDEX IF NOT EXISTS idx_vision_cache_created ON vision_cache(created_at);
"""


@dataclass(frozen=True, slots=True)
class CachedLabel:
    """The full labelling result, as stored in the cache."""

    sha256: str
    model: str
    caption: str
    image_type: str
    confidence: float
    reasoning: str | None
    cost_krw: float
    cost_usd: float
    input_tokens: int
    output_tokens: int


class VisionCache:
    """Tiny SQLite wrapper — open/close per call keeps the API thread-safe."""

    def __init__(self, db_path: Path | str) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self._db_path)) as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def get(self, sha256: str, model: str) -> CachedLabel | None:
        with closing(sqlite3.connect(self._db_path)) as conn:
            row = conn.execute(
                "SELECT sha256, model, caption, image_type, confidence, reasoning, "
                "cost_krw, cost_usd, input_tokens, output_tokens "
                "FROM vision_cache WHERE sha256 = ? AND model = ?",
                (sha256, model),
            ).fetchone()
        if row is None:
            return None
        return CachedLabel(
            sha256=row[0],
            model=row[1],
            caption=row[2],
            image_type=row[3],
            confidence=row[4],
            reasoning=row[5],
            cost_krw=row[6],
            cost_usd=row[7],
            input_tokens=row[8],
            output_tokens=row[9],
        )

    def put(self, label: CachedLabel) -> None:
        with closing(sqlite3.connect(self._db_path)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO vision_cache "
                "(sha256, model, caption, image_type, confidence, reasoning, "
                " cost_krw, cost_usd, input_tokens, output_tokens) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    label.sha256,
                    label.model,
                    label.caption,
                    label.image_type,
                    label.confidence,
                    label.reasoning,
                    label.cost_krw,
                    label.cost_usd,
                    label.input_tokens,
                    label.output_tokens,
                ),
            )
            conn.commit()

    def stats(self) -> dict[str, Any]:
        """Quick health check — total rows + per-model breakdown."""
        with closing(sqlite3.connect(self._db_path)) as conn:
            rows = conn.execute(
                "SELECT model, COUNT(*), SUM(cost_krw) FROM vision_cache GROUP BY model"
            ).fetchall()
        out: dict[str, Any] = {
            "db_path": str(self._db_path),
            "total_rows": sum(int(r[1]) for r in rows),
            "by_model": {r[0]: {"rows": int(r[1]), "saved_krw": r[2] or 0.0} for r in rows},
        }
        return out
