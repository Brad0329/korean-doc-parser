"""kdp-label CLI tests (argparse + entry-point wiring)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from PIL import Image

from korean_doc_parser.cli.label import _build_parser, _load_dotenv, main


@pytest.fixture
def tiny_png(tmp_path: Path) -> Path:
    p = tmp_path / "img.png"
    Image.new("RGB", (8, 8), (0, 200, 100)).save(p, format="PNG")
    return p


def test_argparse_accepts_single_image_arg() -> None:
    parser = _build_parser()
    args = parser.parse_args(["some.png"])
    assert args.image == "some.png"
    assert args.from_document is None
    assert args.model.startswith("claude-")


def test_argparse_accepts_from_document_flag() -> None:
    parser = _build_parser()
    args = parser.parse_args(["--from-document", "doc.pdf"])
    assert args.from_document == "doc.pdf"
    assert args.image is None


def test_argparse_defaults_match_worklog_011() -> None:
    parser = _build_parser()
    args = parser.parse_args(["x.png"])
    # B.1 — reasoning threshold default 0.7
    assert args.threshold == 0.7
    # B.2 — bitmap >= 100x100
    assert args.min_px == 100


def test_no_args_prints_help_and_exits_1(capsys: pytest.CaptureFixture[str]) -> None:
    """Calling kdp-label without target → exit 1, help on stderr."""
    rc = main([])
    captured = capsys.readouterr()
    assert rc == 1
    assert "usage:" in captured.err.lower() or "kdp-label" in captured.err


def test_missing_image_file_exits_1(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    nonexistent = tmp_path / "missing.png"
    rc = main([str(nonexistent), "--no-cache"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "not found" in captured.err.lower()


def test_single_image_writes_json(
    monkeypatch: pytest.MonkeyPatch,
    tiny_png: Path,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """End-to-end CLI with mocked Anthropic — verifies stdout JSON shape."""
    # Patch VisionClient.label to skip real API
    from korean_doc_parser.cli import label as cli_module
    from korean_doc_parser.vision.client import VisionResult

    def fake_label(_self: object, _path: Path) -> VisionResult:
        return VisionResult(
            sha256="fake_sha",
            model="claude-sonnet-4-5",
            caption="모의 캡션",
            image_type="photo",
            confidence=0.9,
            reasoning=None,
            cost_krw=5.0,
            cost_usd=0.0036,
            input_tokens=1500,
            output_tokens=50,
            cache_hit=False,
            second_pass=False,
        )

    monkeypatch.setattr(cli_module.VisionClient, "label", fake_label)

    out_path = tmp_path / "out.json"
    rc = main([str(tiny_png), "--no-cache", "--output", str(out_path)])
    assert rc == 0

    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["caption"] == "모의 캡션"
    assert data["image_type"] == "photo"
    assert data["cost_krw"] == 5.0
    assert data["cache_hit"] is False


def test_load_dotenv_parses_simple_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env = tmp_path / ".env"
    env.write_text(
        "# 주석은 무시\n"
        "FOO=bar\n"
        'QUOTED="quoted value"\n'
        "SINGLE='single quoted'\n"
        "EMPTY_LINE_NEXT=\n"
        "\n"
        "WITH_EQUALS=key=val=more\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("FOO", raising=False)
    monkeypatch.delenv("QUOTED", raising=False)
    monkeypatch.delenv("SINGLE", raising=False)
    monkeypatch.delenv("WITH_EQUALS", raising=False)
    _load_dotenv(env)
    assert os.environ["FOO"] == "bar"
    assert os.environ["QUOTED"] == "quoted value"
    assert os.environ["SINGLE"] == "single quoted"
    assert os.environ["WITH_EQUALS"] == "key=val=more"


def test_load_dotenv_missing_file_is_noop(tmp_path: Path) -> None:
    """No .env → no error, no env mutation."""
    _load_dotenv(tmp_path / "absent.env")  # must not raise


def test_load_dotenv_does_not_overwrite_nonempty_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit shell exports (non-empty) win over .env."""
    env = tmp_path / ".env"
    env.write_text("OVERRIDE_ME=from_dotenv\n", encoding="utf-8")
    monkeypatch.setenv("OVERRIDE_ME", "from_shell")
    _load_dotenv(env)
    assert os.environ["OVERRIDE_ME"] == "from_shell"


def test_load_dotenv_overwrites_empty_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty / whitespace env values are treated as unset (Windows quirk)."""
    env = tmp_path / ".env"
    env.write_text("MAYBE_EMPTY=from_dotenv\n", encoding="utf-8")
    monkeypatch.setenv("MAYBE_EMPTY", "")  # PowerShell-like empty propagation
    _load_dotenv(env)
    assert os.environ["MAYBE_EMPTY"] == "from_dotenv"
