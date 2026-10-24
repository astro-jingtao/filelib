"""MIME detection and image completeness checks."""

from __future__ import annotations

from pathlib import Path

from image_complete.bmp import is_bmp_complete
from image_complete.gif import is_gif_complete
from image_complete.jpg import is_jpg_complete
from image_complete.png import is_png_complete
from image_complete.webp import is_webp_complete
import puremagic

MIME_COMPLETE_CHECKER_MAP = {
    "image/jpeg": is_jpg_complete,
    "image/png": is_png_complete,
    "image/gif": is_gif_complete,
    "image/bmp": is_bmp_complete,
    "image/webp": is_webp_complete,
}

MIME_EXTENSION_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".webp": "image/webp",
}


def get_mime_magic(file_path: Path | str) -> str:
    """Detect the MIME type from file content (puremagic)."""
    return puremagic.from_file(file_path, mime=True)


def get_mime_extension(file_path: Path | str) -> str:
    """Map the file name suffix to a MIME type ('UNKNOWN' when unmapped)."""
    ext = Path(file_path).suffix.lower()
    return MIME_EXTENSION_MAP.get(ext, "UNKNOWN")


def is_file_corrupted(
    file_path: Path | str,
    mime: str | None = None,
    mime_method: str = "magic",
    unsupported_policy: str = "return",
    unsupported_return: bool | None = None,
) -> bool | None:
    """Check whether an image file is corrupted (truncated/incomplete).

    Returns True/False for checkable images; ``unsupported_return``
    (default None) when the detected MIME type has no checker; raises
    ValueError for an invalid ``mime_method``, or for an unsupported
    MIME type with ``unsupported_policy='raise'``. See README for the
    full parameter semantics.
    """
    # image_complete's load() only accepts str/bytes/BytesIO; a Path makes
    # every checker return False (false "corrupted" + "Unhandled data
    # type" noise), so normalize before dispatching.
    file_path = str(file_path)

    if mime is None:
        if mime_method == "magic":
            mime = get_mime_magic(file_path)
        elif mime_method == "extension":
            mime = get_mime_extension(file_path)
        else:
            raise ValueError(f"Invalid mime_method: {mime_method}")

    checker = MIME_COMPLETE_CHECKER_MAP.get(mime)
    if checker is None:
        if unsupported_policy == "return":
            return unsupported_return
        if unsupported_policy == "raise":
            raise ValueError(f"Unsupported MIME type: {mime}")
        raise ValueError(f"Invalid unsupported_policy: {unsupported_policy}")

    return not checker(file_path)
