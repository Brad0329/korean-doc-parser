"""Phase 0 benchmark runner — compare parsers on a shared fixture set.

Walks `benchmarks/fixtures/`, runs every adapter that supports each fixture's
extension, scores the output against the fixture's `.gt.json` ground truth,
and writes both a JSON dump and a Markdown report into `benchmarks/results/`.

Usage (PowerShell):
    python benchmarks/compare.py
    python benchmarks/compare.py --fixtures benchmarks/fixtures --format pdf,docx
    python benchmarks/compare.py --adapters markitdown,docling

Memory measurement uses tracemalloc, which captures Python-allocated bytes
only (not native heap inside docling/marker). This is enough for relative
ordering but is not a true RSS. Cross-process RSS is left to a follow-up.
"""

from __future__ import annotations

import argparse
import gc
import json
import statistics
import sys
import tracemalloc
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

# ruff: noqa: E402 — relative imports below depend on sys.path setup above
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from adapters import ALL_ADAPTERS, BaseAdapter, ParseOutput  # type: ignore[import-not-found]
from metrics import load_ground_truth, score  # type: ignore[import-not-found]

# Only these extensions are treated as fixtures — keeps README.md and other
# bookkeeping files out of the run set.
SUPPORTED_FIXTURE_EXTS = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".hwp", ".hwpx"}


@dataclass
class Run:
    adapter: str
    fixture: str
    extension: str
    ok: bool
    duration_ms: float
    peak_mem_mb: float
    text_length: int
    table_count: int
    image_count: int
    error: str | None = None
    metrics: dict | None = None


@dataclass
class Report:
    started_at: str
    finished_at: str
    fixtures_root: str
    adapter_availability: dict = field(default_factory=dict)
    fixtures: list[str] = field(default_factory=list)
    runs: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def collect_fixtures(root: Path, only_formats: set[str] | None) -> list[Path]:
    if not root.is_dir():
        return []
    files = [
        p
        for p in sorted(root.rglob("*"))
        if p.is_file()
        and p.suffix.lower() in SUPPORTED_FIXTURE_EXTS
        and not p.name.endswith(".gt.json")
    ]
    if only_formats:
        files = [p for p in files if p.suffix.lower().lstrip(".") in only_formats]
    return files


def run_one(adapter: BaseAdapter, fixture: Path) -> tuple[ParseOutput, float]:
    """Run adapter on fixture, capturing peak Python-allocated memory in MB."""
    gc.collect()
    tracemalloc.start()
    try:
        out = adapter.run(fixture)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return out, peak / (1024 * 1024)


def build_adapters(only: set[str] | None) -> list[BaseAdapter]:
    instances: list[BaseAdapter] = []
    for cls in ALL_ADAPTERS:
        a = cls()
        if only and a.name not in only:
            continue
        instances.append(a)
    return instances


def summarize(runs: list[Run]) -> dict:
    by_adapter: dict[str, dict] = {}
    for r in runs:
        b = by_adapter.setdefault(
            r.adapter,
            {
                "runs": 0,
                "ok": 0,
                "errors": 0,
                "durations_ms": [],
                "peak_mem_mb": [],
                "composite_scores": [],
            },
        )
        b["runs"] += 1
        if r.ok:
            b["ok"] += 1
            b["durations_ms"].append(r.duration_ms)
            b["peak_mem_mb"].append(r.peak_mem_mb)
            if r.metrics and r.metrics.get("composite") is not None:
                b["composite_scores"].append(r.metrics["composite"])
        else:
            b["errors"] += 1

    for _name, b in by_adapter.items():
        b["mean_duration_ms"] = _mean(b["durations_ms"])
        b["median_duration_ms"] = _median(b["durations_ms"])
        b["mean_peak_mem_mb"] = _mean(b["peak_mem_mb"])
        b["mean_composite"] = _mean(b["composite_scores"])
        # raw lists are noisy in the report; keep only stats
        del b["durations_ms"]
        del b["peak_mem_mb"]
        del b["composite_scores"]
    return by_adapter


def _mean(xs: list[float]) -> float | None:
    return statistics.fmean(xs) if xs else None


def _median(xs: list[float]) -> float | None:
    return statistics.median(xs) if xs else None


def write_markdown_report(report: Report, path: Path) -> None:
    lines: list[str] = []
    lines.append("# Phase 0 Benchmark Report\n")
    lines.append(f"- started_at: `{report.started_at}`")
    lines.append(f"- finished_at: `{report.finished_at}`")
    lines.append(f"- fixtures_root: `{report.fixtures_root}`")
    lines.append(f"- fixtures: {len(report.fixtures)}")
    lines.append("")
    lines.append("## Adapter availability\n")
    lines.append("| adapter | available |")
    lines.append("|---|---|")
    for name, ok in report.adapter_availability.items():
        lines.append(f"| {name} | {'OK' if ok else 'missing'} |")
    lines.append("")

    lines.append("## Summary (per adapter)\n")
    lines.append(
        "| adapter | runs | ok | errors | mean_ms | median_ms | mean_mem_mb | mean_composite |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for name, b in report.summary.items():
        lines.append(
            "| {a} | {r} | {ok} | {er} | {md} | {me} | {mm} | {mc} |".format(
                a=name,
                r=b["runs"],
                ok=b["ok"],
                er=b["errors"],
                md=_fmt(b["mean_duration_ms"], 1),
                me=_fmt(b["median_duration_ms"], 1),
                mm=_fmt(b["mean_peak_mem_mb"], 2),
                mc=_fmt(b["mean_composite"], 3),
            )
        )
    lines.append("")

    lines.append("## Per-run results\n")
    lines.append(
        "| fixture | ext | adapter | ok | ms | mem_mb | text_len | tables | images | composite | error |"
    )
    lines.append("|---|---|---|---|---:|---:|---:|---:|---:|---:|---|")
    for run in report.runs:
        comp = (run.get("metrics") or {}).get("composite")
        lines.append(
            "| {f} | {ext} | {a} | {ok} | {ms} | {mm} | {tl} | {tc} | {ic} | {cs} | {err} |".format(
                f=run["fixture"],
                ext=run["extension"],
                a=run["adapter"],
                ok="OK" if run["ok"] else "X",
                ms=_fmt(run["duration_ms"], 1),
                mm=_fmt(run["peak_mem_mb"], 2),
                tl=run["text_length"],
                tc=run["table_count"],
                ic=run["image_count"],
                cs=_fmt(comp, 3),
                err=(run.get("error") or "").splitlines()[0][:80] if run.get("error") else "",
            )
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _fmt(v: float | None, digits: int) -> str:
    if v is None:
        return "n/a"
    return f"{v:.{digits}f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 0 parser benchmark runner")
    parser.add_argument("--fixtures", default=str(SCRIPT_DIR / "fixtures"))
    parser.add_argument("--results", default=str(SCRIPT_DIR / "results"))
    parser.add_argument(
        "--format",
        default="",
        help="Comma-separated extensions to include (e.g. pdf,docx). Empty = all.",
    )
    parser.add_argument(
        "--adapters",
        default="",
        help="Comma-separated adapter names to include. Empty = all.",
    )
    args = parser.parse_args(argv)

    only_formats = {x.strip().lower().lstrip(".") for x in args.format.split(",") if x.strip()}
    only_adapters = {x.strip() for x in args.adapters.split(",") if x.strip()}

    fixtures_root = Path(args.fixtures).resolve()
    results_root = Path(args.results).resolve()
    results_root.mkdir(parents=True, exist_ok=True)

    adapters = build_adapters(only_adapters or None)
    if not adapters:
        print("ERROR: no adapters selected.", file=sys.stderr)
        return 2

    fixtures = collect_fixtures(fixtures_root, only_formats or None)
    if not fixtures:
        print(
            f"WARN: no fixtures found under {fixtures_root}. "
            "See benchmarks/fixtures/README.md for the 25-file collection plan.",
            file=sys.stderr,
        )

    started = datetime.now(UTC).isoformat()
    runs: list[Run] = []

    availability = {a.name: a.is_available() for a in adapters}
    print("Adapter availability:")
    for name, ok in availability.items():
        print(f"  - {name}: {'available' if ok else 'MISSING'}")

    for fixture in fixtures:
        ext = fixture.suffix.lower()
        gt = load_ground_truth(fixture)
        for adapter in adapters:
            if not adapter.is_available():
                continue
            if ext not in adapter.supported_formats():
                continue
            print(f"[run] {adapter.name} :: {fixture.name}")
            out, peak_mb = run_one(adapter, fixture)
            metrics_dict: dict | None = None
            if gt is not None and out.error is None:
                metrics_dict = score(out.text, out.table_count, out.image_count, gt).to_dict()
            runs.append(
                Run(
                    adapter=adapter.name,
                    fixture=str(fixture.relative_to(fixtures_root)),
                    extension=ext,
                    ok=out.error is None,
                    duration_ms=out.duration_ms,
                    peak_mem_mb=peak_mb,
                    text_length=len(out.text or ""),
                    table_count=out.table_count,
                    image_count=out.image_count,
                    error=out.error,
                    metrics=metrics_dict,
                )
            )

    finished = datetime.now(UTC).isoformat()
    report = Report(
        started_at=started,
        finished_at=finished,
        fixtures_root=str(fixtures_root),
        adapter_availability=availability,
        fixtures=[str(p.relative_to(fixtures_root)) for p in fixtures],
        runs=[asdict(r) for r in runs],
        summary=summarize(runs),
    )

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = results_root / f"phase0_{stamp}.json"
    md_path = results_root / f"phase0_{stamp}.md"
    json_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown_report(report, md_path)
    print(f"\nWrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
