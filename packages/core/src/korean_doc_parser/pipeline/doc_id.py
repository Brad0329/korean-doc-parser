"""``doc_id`` — sha256 of file bytes, intended as a downstream primary key.

Why a separate helper instead of inlining ``hashlib.sha256(path.read_bytes())``
at every call site: callers (bidwatch / vanasso.kr) need a single canonical
definition so two services keyed off the same file end up with the same
``doc_id``. Centralising this also keeps room for future variants (e.g.
streaming sha256 for large files) without breaking the contract.

Worklog: 019 § 3-2.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def compute_doc_id(path: Path | str) -> str:
    """Return the lowercase-hex sha256 of the file at ``path``.

    The contract is "exact file bytes → 64-char hex". Symlinks are resolved by
    :class:`Path`'s usual read semantics; we don't dereference manually so the
    caller stays in control. Raises :class:`FileNotFoundError` / ``OSError``
    as the underlying read would — callers decide whether to catch.
    """
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
