"""Anthropic Claude Vision wrapper for image labelling (worklog/011 A.1 + B.1).

Two-pass strategy (worklog/011 B.1):
1. Always call with the short prompt (caption + image_type + confidence)
2. If confidence < threshold → second call with reasoning request
3. Cache key = sha256 + model — same image never re-billed (worklog/011 C.4)

The client is opt-in (only available when `pip install korean-doc-parser[vision]`
brings in ``anthropic``). The import is deferred to ``label()`` so importing
this module in a core-only environment doesn't error.
"""

from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, cast

from korean_doc_parser.vision.cache import CachedLabel, VisionCache
from korean_doc_parser.vision.mask import mask_pii
from korean_doc_parser.vision.pricing import DEFAULT_USD_TO_KRW, calculate_cost
from korean_doc_parser.vision.prompts import (
    USER_PROMPT,
    ImageType,
    system_prompt,
    validate_confidence,
    validate_image_type,
)

if TYPE_CHECKING:
    from anthropic import Anthropic
    from anthropic.types import Message

DEFAULT_MODEL: Final[str] = "claude-haiku-4-5"
DEFAULT_REASONING_THRESHOLD: Final[float] = 0.7
DEFAULT_MAX_TOKENS_SHORT: Final[int] = 200
DEFAULT_MAX_TOKENS_WITH_REASONING: Final[int] = 500


@dataclass(frozen=True, slots=True)
class VisionResult:
    """One image's Vision labelling outcome.

    Carries everything the CLI needs to emit as JSON + everything the v0.5
    Pipeline needs to write to ``cost_log`` / ``image_label_cache``.
    """

    sha256: str
    model: str
    caption: str
    image_type: ImageType
    confidence: float
    reasoning: str | None
    cost_krw: float
    cost_usd: float
    input_tokens: int
    output_tokens: int
    cache_hit: bool
    second_pass: bool  # True if reasoning was fetched via a 2nd API call


class VisionClient:
    """Single-image labelling with cache + 2-pass + PII masking."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        cache: VisionCache | None = None,
        reasoning_threshold: float = DEFAULT_REASONING_THRESHOLD,
        usd_to_krw: float = DEFAULT_USD_TO_KRW,
    ) -> None:
        self._model = model
        self._cache = cache
        self._reasoning_threshold = reasoning_threshold
        self._usd_to_krw = usd_to_krw
        self._api_key = api_key  # passed straight to Anthropic SDK; None → env

    def _client(self) -> Anthropic:
        """Lazy-import Anthropic SDK so core-only installs don't error."""
        from anthropic import Anthropic

        return Anthropic(api_key=self._api_key) if self._api_key else Anthropic()

    def label(self, image_path: Path | str) -> VisionResult:
        """Label one image; returns full ``VisionResult``.

        Flow:
        1. sha256(image) → cache lookup, return CachedLabel.* on hit
        2. 1st API call (short prompt) → parse caption/type/confidence
        3. If confidence < threshold → 2nd API call (with reasoning prompt)
        4. PII-mask caption + reasoning
        5. Store in cache under (sha256, model)
        """
        path = Path(image_path)
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        mime = mimetypes.guess_type(path.name)[0] or "image/png"

        # 1) Cache lookup
        if self._cache is not None:
            cached = self._cache.get(sha, self._model)
            if cached is not None:
                return VisionResult(
                    sha256=cached.sha256,
                    model=cached.model,
                    caption=cached.caption,
                    image_type=cast(ImageType, cached.image_type),
                    confidence=cached.confidence,
                    reasoning=cached.reasoning,
                    cost_krw=cached.cost_krw,
                    cost_usd=cached.cost_usd,
                    input_tokens=cached.input_tokens,
                    output_tokens=cached.output_tokens,
                    cache_hit=True,
                    second_pass=False,
                )

        # 2) 1st API call — short prompt
        client = self._client()
        first_msg = self._call_api(client, data, mime, with_reasoning=False)
        first_parsed = _parse_json_reply(first_msg.content[0].text)  # type: ignore[union-attr]
        caption = mask_pii(str(first_parsed.get("caption", "")))
        image_type = validate_image_type(str(first_parsed.get("image_type", "other")))
        confidence = validate_confidence(first_parsed.get("confidence", 0.5))
        reasoning: str | None = None

        first_cost = calculate_cost(
            model=self._model,
            input_tokens=first_msg.usage.input_tokens,
            output_tokens=first_msg.usage.output_tokens,
            usd_to_krw=self._usd_to_krw,
        )
        total_input = first_msg.usage.input_tokens
        total_output = first_msg.usage.output_tokens
        total_cost_krw = first_cost.cost_krw
        total_cost_usd = first_cost.cost_usd
        second_pass = False

        # 3) 2nd API call — reasoning if confidence low
        if confidence < self._reasoning_threshold:
            second_pass = True
            second_msg = self._call_api(client, data, mime, with_reasoning=True)
            second_parsed = _parse_json_reply(second_msg.content[0].text)  # type: ignore[union-attr]
            # Use the second pass's caption/type/confidence too — model may
            # refine when given more output budget
            caption = mask_pii(str(second_parsed.get("caption", caption)))
            image_type = validate_image_type(str(second_parsed.get("image_type", image_type)))
            confidence = validate_confidence(second_parsed.get("confidence", confidence))
            raw_reasoning = second_parsed.get("reasoning", "")
            reasoning = mask_pii(str(raw_reasoning)) if raw_reasoning else None

            second_cost = calculate_cost(
                model=self._model,
                input_tokens=second_msg.usage.input_tokens,
                output_tokens=second_msg.usage.output_tokens,
                usd_to_krw=self._usd_to_krw,
            )
            total_input += second_msg.usage.input_tokens
            total_output += second_msg.usage.output_tokens
            total_cost_krw += second_cost.cost_krw
            total_cost_usd += second_cost.cost_usd

        # 4) Cache write
        if self._cache is not None:
            self._cache.put(
                CachedLabel(
                    sha256=sha,
                    model=self._model,
                    caption=caption,
                    image_type=image_type,
                    confidence=confidence,
                    reasoning=reasoning,
                    cost_krw=total_cost_krw,
                    cost_usd=total_cost_usd,
                    input_tokens=total_input,
                    output_tokens=total_output,
                )
            )

        return VisionResult(
            sha256=sha,
            model=self._model,
            caption=caption,
            image_type=image_type,
            confidence=confidence,
            reasoning=reasoning,
            cost_krw=total_cost_krw,
            cost_usd=total_cost_usd,
            input_tokens=total_input,
            output_tokens=total_output,
            cache_hit=False,
            second_pass=second_pass,
        )

    def _call_api(
        self,
        client: Anthropic,
        image_bytes: bytes,
        mime_type: str,
        *,
        with_reasoning: bool,
    ) -> Message:
        """Single Anthropic Vision call with our standard prompt + image."""
        encoded = base64.standard_b64encode(image_bytes).decode("ascii")
        max_tokens = (
            DEFAULT_MAX_TOKENS_WITH_REASONING if with_reasoning else DEFAULT_MAX_TOKENS_SHORT
        )
        # Anthropic SDK's content type unions are strict TypedDicts — ignoring
        # the structural mismatch is the standard pattern in the docs.
        content: list[Any] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": encoded,
                },
            },
            {"type": "text", "text": USER_PROMPT},
        ]
        return client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system_prompt(with_reasoning=with_reasoning),
            messages=[{"role": "user", "content": content}],
        )


# JSON occasionally arrives wrapped in markdown fences (```json ... ```);
# strip those defensively before json.loads. If parsing still fails we return
# a zero-confidence fallback so the cache layer doesn't poison subsequent runs.
_JSON_FENCE_RE: Final[re.Pattern[str]] = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _parse_json_reply(text: str) -> dict[str, Any]:
    if not text:
        return {"caption": "", "image_type": "other", "confidence": 0.0}
    candidate = text.strip()
    fence_match = _JSON_FENCE_RE.search(candidate)
    if fence_match:
        candidate = fence_match.group(1)
    try:
        loaded = json.loads(candidate)
        return loaded if isinstance(loaded, dict) else {}
    except json.JSONDecodeError:
        return {
            "caption": text[:200],
            "image_type": "other",
            "confidence": 0.0,
        }
