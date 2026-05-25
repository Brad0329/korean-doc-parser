"""Pricing calculator unit tests (worklog/011 A.4)."""

from __future__ import annotations

import pytest

from korean_doc_parser.vision.pricing import (
    DEFAULT_USD_TO_KRW,
    calculate_cost,
)


def test_sonnet_basic_input_output() -> None:
    """1500 in + 100 out at Sonnet = (1500*3 + 100*15) / 1M = $0.006."""
    cost = calculate_cost(
        model="claude-sonnet-4-5",
        input_tokens=1500,
        output_tokens=100,
    )
    assert cost.cost_usd == pytest.approx(0.006, rel=0.01)
    assert cost.cost_krw == pytest.approx(0.006 * DEFAULT_USD_TO_KRW, rel=0.01)


def test_haiku_is_cheapest() -> None:
    haiku = calculate_cost(model="claude-haiku-4-5", input_tokens=1000, output_tokens=100)
    sonnet = calculate_cost(model="claude-sonnet-4-5", input_tokens=1000, output_tokens=100)
    opus = calculate_cost(model="claude-opus-4-5", input_tokens=1000, output_tokens=100)
    assert haiku.cost_usd < sonnet.cost_usd < opus.cost_usd


def test_unknown_model_falls_back_to_sonnet() -> None:
    unknown = calculate_cost(model="claude-future-99", input_tokens=1000, output_tokens=100)
    sonnet = calculate_cost(model="claude-sonnet-4-5", input_tokens=1000, output_tokens=100)
    assert unknown.cost_usd == pytest.approx(sonnet.cost_usd)


def test_cache_read_is_90pct_cheaper() -> None:
    """Anthropic cache_read = 10% of input price → 90% discount."""
    base = calculate_cost(model="claude-sonnet-4-5", input_tokens=1000, output_tokens=0)
    with_cache = calculate_cost(
        model="claude-sonnet-4-5",
        input_tokens=0,
        output_tokens=0,
        cache_read_input_tokens=1000,
    )
    assert with_cache.cost_usd == pytest.approx(base.cost_usd * 0.10, rel=0.01)


def test_cache_creation_surcharge() -> None:
    """cache_creation = 125% of input price."""
    creation = calculate_cost(
        model="claude-sonnet-4-5",
        input_tokens=0,
        output_tokens=0,
        cache_creation_input_tokens=1000,
    )
    base = calculate_cost(model="claude-sonnet-4-5", input_tokens=1000, output_tokens=0)
    assert creation.cost_usd == pytest.approx(base.cost_usd * 1.25, rel=0.01)


def test_custom_fx_rate() -> None:
    cost = calculate_cost(
        model="claude-sonnet-4-5",
        input_tokens=1000,
        output_tokens=0,
        usd_to_krw=1500.0,
    )
    assert cost.usd_to_krw == 1500.0
    assert cost.cost_krw == pytest.approx(cost.cost_usd * 1500.0)


def test_breakdown_preserves_token_counts() -> None:
    cost = calculate_cost(
        model="claude-sonnet-4-5",
        input_tokens=1234,
        output_tokens=567,
        cache_read_input_tokens=89,
        cache_creation_input_tokens=12,
    )
    assert cost.input_tokens == 1234
    assert cost.output_tokens == 567
    assert cost.cache_read_input_tokens == 89
    assert cost.cache_creation_input_tokens == 12
