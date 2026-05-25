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
from contextlib import closing, suppress
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
    hit_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (sha256, model)
);
CREATE INDEX IF NOT EXISTS idx_vision_cache_created ON vision_cache(created_at);
"""

# v0.5.0 — hit_count migration for existing v0.4.x caches that pre-date the
# column. ``ALTER TABLE ADD COLUMN`` is idempotent only via a probe; we wrap
# it in a try/except so brand-new caches (already on the v0.5 schema) skip
# silently.
_MIGRATIONS = ("ALTER TABLE vision_cache ADD COLUMN hit_count INTEGER NOT NULL DEFAULT 0",)


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
            # ``OperationalError`` is raised when the column already exists on
            # a fresh v0.5+ DB — suppress silently so the migration is idempotent.
            for migration in _MIGRATIONS:
                with suppress(sqlite3.OperationalError):
                    conn.execute(migration)
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
            # v0.5.0 (worklog/019 § 3-4): increment hit_count on read so
            # operators can compute real cache hit rate via ``stats()``.
            conn.execute(
                "UPDATE vision_cache SET hit_count = hit_count + 1 WHERE sha256 = ? AND model = ?",
                (sha256, model),
            )
            conn.commit()
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
        """Operational visibility — total / per-model / per-date breakdown.

        Used by ``kdp-label --stats`` (v0.4.3, worklog/015). ``saved_krw`` is the
        cumulative spend that was avoided on cache hits — counted at the moment
        each row was written (i.e. the cost we would have paid had we *not*
        cached). ``by_date`` groups rows by ``created_at`` (UTC date) so
        operators can spot spikes; the ``by_model`` sub-breakdown inside each
        date row matters when running Sonnet+Haiku side by side.
        """
        with closing(sqlite3.connect(self._db_path)) as conn:
            model_rows = conn.execute(
                "SELECT model, COUNT(*), SUM(cost_krw), COALESCE(SUM(hit_count), 0) "
                "FROM vision_cache GROUP BY model"
            ).fetchall()
            date_rows = conn.execute(
                "SELECT date(created_at) AS d, model, COUNT(*), SUM(cost_krw) "
                "FROM vision_cache GROUP BY d, model ORDER BY d"
            ).fetchall()
            last_7 = conn.execute(
                "SELECT COALESCE(SUM(cost_krw), 0.0) FROM vision_cache "
                "WHERE date(created_at) >= date('now', '-6 days')"
            ).fetchone()
            total_hits_row = conn.execute(
                "SELECT COALESCE(SUM(hit_count), 0) FROM vision_cache"
            ).fetchone()

        by_date: dict[str, dict[str, Any]] = {}
        for d, model, count, cost in date_rows:
            entry = by_date.setdefault(d, {"rows": 0, "cost_krw": 0.0, "by_model": {}})
            entry["rows"] += int(count)
            entry["cost_krw"] = round(entry["cost_krw"] + (cost or 0.0), 2)
            entry["by_model"][model] = {
                "rows": int(count),
                "cost_krw": round(cost or 0.0, 2),
            }

        total_rows = sum(int(r[1]) for r in model_rows)
        total_hits = int(total_hits_row[0] if total_hits_row else 0)
        return {
            "db_path": str(self._db_path),
            "total_rows": total_rows,
            "total_saved_krw": round(sum((r[2] or 0.0 for r in model_rows), 0.0), 2),
            "total_hit_count": total_hits,
            "hit_rate": round(total_hits / (total_hits + total_rows), 3)
            if (total_hits + total_rows) > 0
            else 0.0,
            "by_model": {
                r[0]: {
                    "rows": int(r[1]),
                    "saved_krw": round(r[2] or 0.0, 2),
                    "hit_count": int(r[3]),
                }
                for r in model_rows
            },
            "by_date": by_date,
            "last_7_days_saved_krw": round(last_7[0] if last_7 else 0.0, 2),
        }
