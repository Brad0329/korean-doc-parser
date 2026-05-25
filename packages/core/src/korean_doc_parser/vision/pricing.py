"""Claude API pricing — converts token usage to KRW (worklog/011 A.4).

Prices reflect the public Anthropic catalog as of 2026-05. They live in code
rather than a config file so the per-version pricing assumption is auditable
via git blame. When Anthropic changes prices, bump this table + add a
worklog entry documenting the new baseline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# USD per 1M tokens. Source: console.anthropic.com pricing page, 2026-05.
_PRICING_USD_PER_M: Final[dict[str, tuple[float, float]]] = {
    # model_id: (input_per_million, output_per_million)
    "claude-haiku-4-5": (0.25, 1.25),
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-opus-4-5": (15.0, 75.0),
    # Aliases — Anthropic SDK may return short names
    "claude-haiku": (0.25, 1.25),
    "claude-sonnet": (3.0, 15.0),
    "claude-opus": (15.0, 75.0),
}

# KRW per USD. Conservative — bump when FX shifts meaningfully.
# v0.4 baseline 2026-05: ~1380. Updated via worklog entry.
DEFAULT_USD_TO_KRW: Final[float] = 1380.0


@dataclass(frozen=True, slots=True)
class CostBreakdown:
    """Per-call cost in both USD and KRW.

    All fields kept explicit so downstream (cost_log table in v0.5+) can
    aggregate by token type / model / FX rate without re-deriving.
    """

    model: str
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int
    cost_usd: float
    cost_krw: float
    usd_to_krw: float


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_input_tokens: int = 0,
    cache_creation_input_tokens: int = 0,
    usd_to_krw: float = DEFAULT_USD_TO_KRW,
) -> CostBreakdown:
    """Compute per-call cost from Anthropic SDK usage fields.

    Prompt caching pricing (Anthropic 2026-05):
    * cache_read = 10% of input cost (90% discount)
    * cache_creation = 125% of input cost (one-time write surcharge)
    Regular ``input_tokens`` from the SDK excludes the cache-related counts.
    """
    in_price, out_price = _PRICING_USD_PER_M.get(model, (3.0, 15.0))  # fallback to Sonnet

    cost_usd = (
        input_tokens * in_price / 1_000_000.0
        + output_tokens * out_price / 1_000_000.0
        + cache_read_input_tokens * in_price * 0.10 / 1_000_000.0
        + cache_creation_input_tokens * in_price * 1.25 / 1_000_000.0
    )
    cost_krw = cost_usd * usd_to_krw

    return CostBreakdown(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_input_tokens=cache_read_input_tokens,
        cache_creation_input_tokens=cache_creation_input_tokens,
        cost_usd=cost_usd,
        cost_krw=cost_krw,
        usd_to_krw=usd_to_krw,
    )
