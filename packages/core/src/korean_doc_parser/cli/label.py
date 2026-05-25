"""``kdp-label`` — Claude Vision labelling CLI (worklog/011 § 9).

Two modes:
* Single image: ``kdp-label image.png`` → one JSON object on stdout
* Document mode: ``kdp-label --from-document proposal.pdf`` → JSONL,
  one labelled image per line

Both modes share the same per-image pipeline:
1. sha256 + model cache lookup (skip API on hit)
2. Vision call (with 2-pass for low-confidence per B.1)
3. PII-mask caption + reasoning
4. Cost + token usage attached for downstream cost tracking

Exit codes:
* 0 = success
* 1 = config/usage error (no API key, missing file, etc.)
* 2 = runtime error inside Vision call
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import TextIO

from korean_doc_parser.exceptions import KoreanDocParserError
from korean_doc_parser.vision.cache import VisionCache
from korean_doc_parser.vision.client import (
    DEFAULT_MODEL,
    DEFAULT_REASONING_THRESHOLD,
    VisionClient,
)
from korean_doc_parser.vision.pricing import DEFAULT_USD_TO_KRW

DEFAULT_CACHE_PATH: str = "~/.kdp-cache.db"
DEFAULT_MIN_PX: int = 100  # B.2 — bitmap >= 100x100 px


def _load_dotenv(env_path: Path = Path(".env")) -> None:
    """Tiny KEY=VALUE loader — no python-dotenv dependency.

    Supports unquoted (``KEY=value``) and quoted (``KEY="value"`` /
    ``KEY='value'``) forms. Lines starting with ``#`` are comments.

    Existing ``os.environ`` values win **only if they are non-empty** —
    PowerShell on Windows propagates empty-string env vars by default, and
    ``setdefault`` would treat that as "already set" and silently ignore the
    ``.env``. Explicit ``setx`` / shell exports still take precedence.
    """
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key and not os.environ.get(key, "").strip():
            os.environ[key] = value


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()  # opt-in: only acts if ./.env exists
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.stats:
        return _run_stats(args)

    try:
        client = _build_client(args)
    except KoreanDocParserError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.from_document:
        return _run_from_document(client, Path(args.from_document), args)
    if args.image:
        return _run_single_image(client, Path(args.image), args.output)
    parser.print_help(sys.stderr)
    return 1


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="kdp-label",
        description="Claude Vision labelling for document images (v0.4).",
    )
    p.add_argument(
        "image",
        nargs="?",
        help="Path to a single image file (PNG/JPEG). Mutually exclusive with --from-document.",
    )
    p.add_argument(
        "--from-document",
        metavar="PATH",
        help="Extract images from a document (PDF/DOCX/HWPX/HWP) then label each.",
    )
    p.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Anthropic Claude model id (default: {DEFAULT_MODEL}).",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_REASONING_THRESHOLD,
        help=f"Reasoning request threshold (default: {DEFAULT_REASONING_THRESHOLD}).",
    )
    p.add_argument(
        "--cache-path",
        default=DEFAULT_CACHE_PATH,
        help=f"SQLite cache file (default: {DEFAULT_CACHE_PATH}).",
    )
    p.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable cache for this run (still consults env API).",
    )
    p.add_argument(
        "--min-px",
        type=int,
        default=DEFAULT_MIN_PX,
        help=f"Document mode: skip images smaller than this (default: {DEFAULT_MIN_PX} px on each side).",
    )
    p.add_argument(
        "--usd-to-krw",
        type=float,
        default=DEFAULT_USD_TO_KRW,
        help=f"FX rate for cost_krw (default: {DEFAULT_USD_TO_KRW}).",
    )
    p.add_argument(
        "--output",
        default="-",
        help="Output file path (default: stdout).",
    )
    p.add_argument(
        "--stats",
        action="store_true",
        help="Print cache stats as JSON (rows / saved cost by model+date) and exit. "
        "Other positional/document args are ignored.",
    )
    return p


def _build_client(args: argparse.Namespace) -> VisionClient:
    cache: VisionCache | None = None
    if not args.no_cache:
        cache_path = Path(args.cache_path).expanduser()
        cache = VisionCache(cache_path)
    return VisionClient(
        model=args.model,
        cache=cache,
        reasoning_threshold=args.threshold,
        usd_to_krw=args.usd_to_krw,
    )


def _run_single_image(client: VisionClient, image_path: Path, output: str) -> int:
    if not image_path.is_file():
        print(f"ERROR: image not found: {image_path}", file=sys.stderr)
        return 1
    try:
        result = client.label(image_path)
    except Exception as exc:
        print(f"ERROR: Vision call failed: {exc}", file=sys.stderr)
        return 2
    sink = _open_sink(output)
    try:
        sink.write(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        sink.write("\n")
    finally:
        if output != "-":
            sink.close()
    return 0


def _run_from_document(client: VisionClient, doc_path: Path, args: argparse.Namespace) -> int:
    if not doc_path.is_file():
        print(f"ERROR: document not found: {doc_path}", file=sys.stderr)
        return 1

    from korean_doc_parser import extract

    try:
        result = extract(doc_path)
    except Exception as exc:
        print(f"ERROR: failed to extract images from {doc_path}: {exc}", file=sys.stderr)
        return 2

    all_images = result.images
    candidates = [
        img
        for img in all_images
        if img.file_path and img.width >= args.min_px and img.height >= args.min_px
    ]
    skipped = len(all_images) - len(candidates)

    print(
        f"Extracted {len(all_images)} images from {doc_path.name}.",
        file=sys.stderr,
    )
    print(
        f"Filtered: {len(candidates)} images >= {args.min_px}x{args.min_px} "
        f"({skipped} too small / no bitmap, skipped).",
        file=sys.stderr,
    )

    sink = _open_sink(args.output)
    started = time.perf_counter()
    total_cost_krw = 0.0
    cache_hits = 0
    try:
        for idx, img in enumerate(candidates, start=1):
            try:
                vr = client.label(Path(img.file_path))
            except Exception as exc:
                print(
                    f"[{idx}/{len(candidates)}] ERROR sha={img.sha256[:8]}: {exc}",
                    file=sys.stderr,
                )
                continue
            sink.write(json.dumps(asdict(vr), ensure_ascii=False))
            sink.write("\n")
            sink.flush()
            total_cost_krw += vr.cost_krw
            cache_hits += 1 if vr.cache_hit else 0
            print(
                f"[{idx}/{len(candidates)}] page={img.page_no} "
                f"type={vr.image_type} conf={vr.confidence:.2f} "
                f"{'(cache)' if vr.cache_hit else ''}"
                f"{' (2-pass)' if vr.second_pass else ''} "
                f"cost={vr.cost_krw:.2f}원",
                file=sys.stderr,
            )
    finally:
        if args.output != "-":
            sink.close()

    elapsed = time.perf_counter() - started
    print(
        f"\nTotal: {len(candidates)} images / {total_cost_krw:.0f}원 / "
        f"{elapsed:.0f}초 / cache_hits: {cache_hits}",
        file=sys.stderr,
    )
    return 0


def _run_stats(args: argparse.Namespace) -> int:
    """``--stats`` — dump cache.stats() as JSON and exit (worklog/015).

    Does not touch the Anthropic API or even the Vision client. If the cache
    file is missing we refuse to create an empty one (silent creation would
    mask user errors like a typo in ``--cache-path``).
    """
    cache_path = Path(args.cache_path).expanduser()
    if not cache_path.is_file():
        print(
            f"ERROR: cache file not found: {cache_path}\n"
            "  Run `kdp-label` on at least one image first, or pass --cache-path.",
            file=sys.stderr,
        )
        return 1
    data = VisionCache(cache_path).stats()
    sink = _open_sink(args.output)
    try:
        sink.write(json.dumps(data, ensure_ascii=False, indent=2))
        sink.write("\n")
    finally:
        if args.output != "-":
            sink.close()
    return 0


def _open_sink(output: str) -> TextIO:
    if output == "-":
        return sys.stdout
    return Path(output).open("w", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
