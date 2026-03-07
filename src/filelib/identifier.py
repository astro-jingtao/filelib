from __future__ import annotations

from pathlib import Path

import puremagic
from image_complete.jpg import is_jpg_complete
from image_complete.png import is_png_complete
from image_complete.gif import is_gif_complete
from image_complete.bmp import is_bmp_complete
from image_complete.webp import is_webp_complete

MINE_COMPLETE_CHECKER_MAP = {
    'image/jpeg': is_jpg_complete,
    'image/png': is_png_complete,
    'image/gif': is_gif_complete,
    'image/bmp': is_bmp_complete,
    'image/webp': is_webp_complete
}

MINE_EXTENSION_MAP = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.bmp': 'image/bmp',
    '.webp': 'image/webp'
}


def get_mime_magic(file_path: Path | str) -> str:
    return puremagic.from_file(file_path, mime=True)


def get_mime_extension(file_path: Path | str) -> str:
    ext = Path(file_path).suffix.lower()
    return MINE_EXTENSION_MAP.get(ext, 'UNKNOWN')


def is_file_corrupted(file_path: Path | str,
                      mime=None,
                      mime_method='magic',
                      unsupported_policy='return',
                      unsupported_return=None) -> bool | None:
    if mime is None:
        if mime_method == 'magic':
            mime = get_mime_magic(file_path)
        elif mime_method == 'extension':
            mime = get_mime_extension(file_path)
        else:
            raise ValueError(f'Invalid mime_method: {mime_method}')

    checker = MINE_COMPLETE_CHECKER_MAP.get(mime)
    if checker is None:
        if unsupported_policy == 'return':
            return unsupported_return
        elif unsupported_policy == 'raise':
            raise ValueError(f'Unsupported MIME type: {mime}')
        else:
            raise ValueError(
                f'Invalid unsupported_policy: {unsupported_policy}')

    return not checker(file_path)
