"""v0.4.2 Sonnet vs Haiku 비교 측정 (worklog/013 § 5-2 통합 patch).

worklog/011 § A.1 의 "v0.4 Vision CLI 평가에서 Haiku 도 동시 측정 후 retreat 가능"
결정을 이행하는 자동화 스크립트입니다. v0.4.1 합성 5건 평가의 한계 (worklog/013
§ 3-1, 6-1) 인 "합성 픽스처 다양성 부족 + confidence 분포 검증 불가" 를 보완하기
위해 samples/ 의 실 PDF/PPTX 이미지로 평가합니다.

사용:

    python scripts/eval_haiku.py samples/some.pdf

같은 sha256 후보 셋을 두 모델에 결정론적 순서 (sha256 정렬) 로 라벨링 →
``{out_dir}/{model}.jsonl`` + ``{out_dir}/summary.json`` 출력.

캐시는 default 비활성 (cold call 비용 측정). ``--cache`` 로 켜기.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

_HANGUL_RE = re.compile(r"[가-힣]")
_LETTER_RE = re.compile(r"\w", re.UNICODE)


def _load_dotenv(env_path: Path = Path(".env")) -> None:
    """``cli/label.py`` 의 ``_load_dotenv`` 와 동일 패턴.

    Anthropic 키를 ``.env`` 에서 자동 로드. 명시적 env var 가 있으면 그게 우선.
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


def hangul_ratio(text: str) -> float:
    """글자(word char) 중 한글 음절 비율. ASCII / 한자 / 숫자는 분모에 포함."""
    if not text:
        return 0.0
    letters = _LETTER_RE.findall(text)
    if not letters:
        return 0.0
    hangul = _HANGUL_RE.findall(text)
    return len(hangul) / len(letters)


def _summarize_model(records: list[dict[str, Any]], wall_s: float) -> dict[str, Any]:
    confidences = [r["confidence"] for r in records]
    costs_krw = [r["cost_krw"] for r in records]
    costs_usd = [r["cost_usd"] for r in records]
    hangul = [r["hangul_ratio"] for r in records]
    types_count: dict[str, int] = {}
    for r in records:
        t = r["image_type"]
        types_count[t] = types_count.get(t, 0) + 1
    n = max(len(records), 1)
    return {
        "n_images": len(records),
        "wall_time_s": round(wall_s, 1),
        "mean_wall_per_image_s": round(wall_s / n, 2),
        "cost_total_krw": round(sum(costs_krw), 2),
        "cost_mean_krw": round(sum(costs_krw) / n, 3),
        "cost_total_usd": round(sum(costs_usd), 4),
        "confidence_mean": round(statistics.mean(confidences), 3) if confidences else 0,
        "confidence_median": round(statistics.median(confidences), 3) if confidences else 0,
        "confidence_min": round(min(confidences), 3) if confidences else 0,
        "confidence_max": round(max(confidences), 3) if confidences else 0,
        "confidence_below_0_7_pct": round(
            100 * sum(1 for c in confidences if c < 0.7) / max(len(confidences), 1), 1
        ),
        "hangul_ratio_mean": round(statistics.mean(hangul), 3) if hangul else 0,
        "hangul_ratio_min": round(min(hangul), 3) if hangul else 0,
        "hangul_ratio_max": round(max(hangul), 3) if hangul else 0,
        "image_types": types_count,
        "second_pass_count": sum(1 for r in records if r["second_pass"]),
        "cache_hit_count": sum(1 for r in records if r["cache_hit"]),
    }


def _cross_model(
    summaries: dict[str, dict[str, Any]],
    per_image: dict[str, list[dict[str, Any]]],
    models: list[str],
) -> dict[str, Any]:
    if len(models) < 2:
        return {}
    m1, m2 = models[0], models[1]
    r1_by_sha = {r["sha256"]: r for r in per_image[m1]}
    r2_by_sha = {r["sha256"]: r for r in per_image[m2]}
    common = set(r1_by_sha) & set(r2_by_sha)
    agree = sum(1 for sha in common if r1_by_sha[sha]["image_type"] == r2_by_sha[sha]["image_type"])
    mean1 = summaries[m1]["cost_mean_krw"]
    mean2 = summaries[m2]["cost_mean_krw"]
    return {
        "models": [m1, m2],
        "common_images": len(common),
        "image_type_agreement": agree,
        "image_type_agreement_pct": round(100 * agree / max(len(common), 1), 1),
        "cost_ratio_m2_over_m1": round(mean2 / mean1, 4) if mean1 > 0 else 0,
    }


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    ap = argparse.ArgumentParser(
        prog="eval_haiku",
        description="v0.4.2 Sonnet vs Haiku 비교 측정 (worklog/013 § 5-2 통합).",
    )
    ap.add_argument("document", help="평가할 문서 경로 (PDF / PPTX / DOCX / HWPX)")
    ap.add_argument(
        "--models",
        nargs="+",
        default=["claude-sonnet-4-5", "claude-haiku-4-5"],
        help="비교할 Anthropic 모델 ID 들 (default: Sonnet + Haiku)",
    )
    ap.add_argument(
        "--out-dir",
        default="eval_v0.4.2",
        help="결과 출력 디렉토리 (default: ./eval_v0.4.2)",
    )
    ap.add_argument("--min-px", type=int, default=100, help="비트맵 최소 px (default: 100)")
    ap.add_argument("--limit", type=int, default=None, help="이미지 개수 상한 (default: 무제한)")
    ap.add_argument(
        "--cache",
        action="store_true",
        help="cache 활성 (default: 비활성, cold 비용 측정)",
    )
    ap.add_argument(
        "--cache-path",
        default="~/.kdp-cache.db",
        help="cache SQLite 경로 (--cache 시만 사용)",
    )
    ap.add_argument("--usd-to-krw", type=float, default=1380.0)
    args = ap.parse_args(argv)

    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print(
            "ERROR: ANTHROPIC_API_KEY 가 없습니다. .env 파일에 박거나 env var 로 설정.",
            file=sys.stderr,
        )
        return 1

    doc = Path(args.document)
    if not doc.is_file():
        print(f"ERROR: 문서 없음: {doc}", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Lazy import — vision extras 없을 때 ImportError 를 .env 확인 후로 미룸
    from korean_doc_parser import extract
    from korean_doc_parser.vision.cache import VisionCache
    from korean_doc_parser.vision.client import VisionClient

    print(f"[1] extract {doc.name} ...", file=sys.stderr)
    result = extract(doc)
    all_imgs = result.images
    big = [
        img
        for img in all_imgs
        if img.file_path and img.width >= args.min_px and img.height >= args.min_px
    ]
    big.sort(key=lambda i: i.sha256)
    if args.limit is not None:
        big = big[: args.limit]
    print(
        f"  → total={len(all_imgs)}, big(>= {args.min_px}px)={len(big)}, 평가 대상={len(big)}",
        file=sys.stderr,
    )

    # candidates 동결 — sha256 리스트를 박아 재현성 확보
    candidates_path = out_dir / "candidates.json"
    candidates_path.write_text(
        json.dumps(
            [
                {
                    "idx": idx,
                    "sha256": img.sha256,
                    "page_no": img.page_no,
                    "width": img.width,
                    "height": img.height,
                    "file_path": str(img.file_path),
                }
                for idx, img in enumerate(big, start=1)
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"  → candidates 동결: {candidates_path}", file=sys.stderr)

    cache: VisionCache | None = None
    if args.cache:
        cache = VisionCache(Path(args.cache_path).expanduser())

    summaries: dict[str, dict[str, Any]] = {}
    per_image_records: dict[str, list[dict[str, Any]]] = {}

    for m_idx, model in enumerate(args.models, start=2):
        print(
            f"\n[{m_idx}] {model} 평가 ({len(big)} 이미지)",
            file=sys.stderr,
        )
        client = VisionClient(model=model, cache=cache, usd_to_krw=args.usd_to_krw)
        jsonl_path = out_dir / f"{model.replace('/', '_')}.jsonl"
        started = time.perf_counter()
        records: list[dict[str, Any]] = []
        with jsonl_path.open("w", encoding="utf-8") as f:
            for idx, img in enumerate(big, start=1):
                t0 = time.perf_counter()
                try:
                    vr = client.label(Path(img.file_path))
                except Exception as exc:
                    print(
                        f"  [{idx}/{len(big)}] ERROR sha={img.sha256[:8]}: {exc}",
                        file=sys.stderr,
                    )
                    continue
                dt_ms = int((time.perf_counter() - t0) * 1000)
                record = asdict(vr)
                record["page_no"] = img.page_no
                record["width"] = img.width
                record["height"] = img.height
                record["dt_ms"] = dt_ms
                record["hangul_ratio"] = hangul_ratio(vr.caption)
                f.write(json.dumps(record, ensure_ascii=False))
                f.write("\n")
                f.flush()
                records.append(record)
                print(
                    f"  [{idx}/{len(big)}] type={vr.image_type} "
                    f"conf={vr.confidence:.2f} hangul={record['hangul_ratio'] * 100:.0f}% "
                    f"cost={vr.cost_krw:.2f}원 dt={dt_ms}ms"
                    f"{' (cache)' if vr.cache_hit else ''}"
                    f"{' (2-pass)' if vr.second_pass else ''}",
                    file=sys.stderr,
                )
        elapsed = time.perf_counter() - started
        per_image_records[model] = records
        summaries[model] = _summarize_model(records, elapsed)

    cross = _cross_model(summaries, per_image_records, args.models)

    summary_path = out_dir / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "document": str(doc),
                "n_candidates": len(big),
                "per_model": summaries,
                "cross_model": cross,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n→ summary: {summary_path}", file=sys.stderr)
    print(json.dumps({"per_model": summaries, "cross_model": cross}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
