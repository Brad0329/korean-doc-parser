"""SQLite Vision cache unit tests (worklog/011 C.4)."""

from __future__ import annotations

from pathlib import Path

from korean_doc_parser.vision.cache import CachedLabel, VisionCache


def _make_label(sha: str, model: str = "claude-sonnet-4-5") -> CachedLabel:
    return CachedLabel(
        sha256=sha,
        model=model,
        caption="테스트 캡션",
        image_type="chart",
        confidence=0.85,
        reasoning=None,
        cost_krw=8.25,
        cost_usd=0.006,
        input_tokens=1500,
        output_tokens=100,
    )


def test_get_returns_none_when_empty(tmp_path: Path) -> None:
    cache = VisionCache(tmp_path / "cache.db")
    assert cache.get("abc123", "claude-sonnet-4-5") is None


def test_put_then_get_roundtrip(tmp_path: Path) -> None:
    cache = VisionCache(tmp_path / "cache.db")
    label = _make_label("sha_one")
    cache.put(label)
    fetched = cache.get("sha_one", "claude-sonnet-4-5")
    assert fetched is not None
    assert fetched.caption == "테스트 캡션"
    assert fetched.confidence == 0.85
    assert fetched.cost_krw == 8.25


def test_different_models_get_different_rows(tmp_path: Path) -> None:
    """Cache key is (sha, model) — same image under different model = separate."""
    cache = VisionCache(tmp_path / "cache.db")
    cache.put(_make_label("dup_sha", model="claude-sonnet-4-5"))
    cache.put(_make_label("dup_sha", model="claude-haiku-4-5"))
    assert cache.get("dup_sha", "claude-sonnet-4-5") is not None
    assert cache.get("dup_sha", "claude-haiku-4-5") is not None


def test_put_replaces_existing_row(tmp_path: Path) -> None:
    """INSERT OR REPLACE — re-caching same key updates the row."""
    cache = VisionCache(tmp_path / "cache.db")
    cache.put(_make_label("sha_repl"))
    refined = CachedLabel(
        sha256="sha_repl",
        model="claude-sonnet-4-5",
        caption="개선된 캡션",
        image_type="chart",
        confidence=0.95,
        reasoning="더 명확함",
        cost_krw=10.0,
        cost_usd=0.0072,
        input_tokens=1500,
        output_tokens=200,
    )
    cache.put(refined)
    fetched = cache.get("sha_repl", "claude-sonnet-4-5")
    assert fetched is not None
    assert fetched.caption == "개선된 캡션"
    assert fetched.reasoning == "더 명확함"
    assert fetched.confidence == 0.95


def test_stats_reports_per_model(tmp_path: Path) -> None:
    cache = VisionCache(tmp_path / "cache.db")
    cache.put(_make_label("sha_a", model="claude-sonnet-4-5"))
    cache.put(_make_label("sha_b", model="claude-sonnet-4-5"))
    cache.put(_make_label("sha_c", model="claude-haiku-4-5"))
    stats = cache.stats()
    assert stats["total_rows"] == 3
    assert stats["by_model"]["claude-sonnet-4-5"]["rows"] == 2
    assert stats["by_model"]["claude-haiku-4-5"]["rows"] == 1


def test_cache_persists_across_instances(tmp_path: Path) -> None:
    """File-backed → new VisionCache instance sees prior writes."""
    db = tmp_path / "cache.db"
    cache_a = VisionCache(db)
    cache_a.put(_make_label("persisted"))
    del cache_a
    cache_b = VisionCache(db)
    fetched = cache_b.get("persisted", "claude-sonnet-4-5")
    assert fetched is not None
