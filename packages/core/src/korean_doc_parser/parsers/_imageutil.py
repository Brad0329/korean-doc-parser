"""Shared image utilities for parsers (v0.5.0, worklog/019 § 3-4).

Pulled out of ``parsers/pptx.py`` + ``packages/hwp/.../parser.py`` where the
same 8-line PIL helper was duplicated (worklog/017 § 4-4). Keeping it in
``packages/core/.../parsers/`` lets the HWP package import it across the
package boundary — that direction is allowed (hwp → core), the reverse
(core → hwp) is not.

PDF doesn't use this helper because pypdf already returns a decoded PIL
Image — see ``parsers/pdf.py::_collect_bitmaps``. If a third parser starts
needing the same logic, this is the place to put it.
"""

from __future__ import annotations

from io import BytesIO


def safe_image_size(data: bytes) -> tuple[int, int]:
    """PIL-based ``(width, height)``; ``(0, 0)`` if PIL can't decode.

    Used for blobs whose format may be non-standard (``.wdp`` / HD Photo in
    PPTX, occasionally exotic image headers from HWP's BinData). The
    contract is "best-effort size for known formats, zeros otherwise" —
    downstream Vision still gets the bytes via ``file_path`` / ``sha256``
    regardless of whether width/height are known.
    """
    from PIL import Image

    try:
        with Image.open(BytesIO(data)) as img:
            return int(img.width), int(img.height)
    except Exception:
        return 0, 0
