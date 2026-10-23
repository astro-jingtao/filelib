"""HTTP downloads over requests, streaming to disk."""
from __future__ import annotations

import os

import requests


def download_response(url: str, filename: str, force: bool = False,
                      verbose: bool = False,
                      timeout: float | None = None) -> int | None:
    """Download ``url`` to ``filename`` with requests (streaming).

    Behavior:
    - An existing ``filename`` with ``force=False`` (default) skips the
      download, prints a note when ``verbose=True``, and returns ``None``.
    - Otherwise the HTTP status code is returned: 200 means the file was
      written; any other status is returned, not raised.
    - Parent directories of ``filename`` are not created; a missing
      parent raises ``FileNotFoundError`` from ``open``.
    - ``timeout`` is passed to requests verbatim (None = no timeout).
    """
    if not force and os.path.exists(filename):
        if verbose:
            print(f"File {filename} already exists. Skipping download.")
        return None

    response = requests.get(url, stream=True, timeout=timeout)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.writelines(response.iter_content(chunk_size=8192))
        if verbose:
            print(f"Download completed successfully for {filename}!")
    else:
        if verbose:
            print(f"Failed to download {filename}: {response.status_code}")

    return response.status_code
