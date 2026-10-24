"""Live checks of download_response against a real remote endpoint.

Skipped unless ``FILELIB_LIVE_TESTS`` is set to a non-empty value:

    FILELIB_LIVE_TESTS=1 python -m pytest tests/test_downloader_live.py -v

Proxy environment variables are honored the way requests honors them.
"""

import os

import pytest

from filelib.downloader import download_response

pytestmark = pytest.mark.skipif(
    not os.environ.get("FILELIB_LIVE_TESTS"),
    reason="set FILELIB_LIVE_TESTS=1 to exercise a real download",
)


class TestLiveDownload:
    def test_live_200_writes_file(self, tmp_path):
        target = tmp_path / "index.html"
        status = download_response("https://www.example.com/", str(target))
        assert status == 200
        assert target.stat().st_size > 0

    def test_live_non_200_returns_status(self, tmp_path):
        target = tmp_path / "missing.html"
        status = download_response("https://www.example.com/no-such-page", str(target))
        assert status == 404
        assert not target.exists()
