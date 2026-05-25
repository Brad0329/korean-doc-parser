"""``korean_doc_parser.pipeline.doc_id`` — sha256 helper tests (v0.5.0)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from korean_doc_parser.pipeline import compute_doc_id


def test_doc_id_returns_64_char_hex(tmp_path: Path) -> None:
    p = tmp_path / "doc.txt"
    p.write_bytes(b"hello korean-doc-parser")
    sha = compute_doc_id(p)
    assert len(sha) == 64
    assert all(c in "0123456789abcdef" for c in sha)


def test_doc_id_matches_hashlib_for_same_bytes(tmp_path: Path) -> None:
    """Contract: ``compute_doc_id`` == ``hashlib.sha256(bytes)`` — must hold so
    callers can verify with off-the-shelf tooling."""
    data = b"\x00\x01\x02\xff\xfeKorean " + "한글".encode() + b"\nmultiline"
    p = tmp_path / "doc.bin"
    p.write_bytes(data)
    assert compute_doc_id(p) == hashlib.sha256(data).hexdigest()


def test_doc_id_accepts_string_path(tmp_path: Path) -> None:
    p = tmp_path / "doc.txt"
    p.write_bytes(b"x")
    assert compute_doc_id(str(p)) == compute_doc_id(p)


def test_doc_id_raises_on_missing_file(tmp_path: Path) -> None:
    """Errors propagate — callers decide whether to catch FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        compute_doc_id(tmp_path / "definitely_missing.txt")


def test_doc_id_empty_file_is_well_known_sha(tmp_path: Path) -> None:
    """Sanity: empty-file sha256 is a published constant — guards against
    accidental ``read_text`` substitution that would mangle empty input."""
    p = tmp_path / "empty"
    p.write_bytes(b"")
    assert compute_doc_id(p) == ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
