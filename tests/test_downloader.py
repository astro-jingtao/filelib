from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

import pytest

from filelib.downloader import download_response

# 大于 8192 字节的下载块，确保流式写入的多块路径被覆盖
PAYLOAD = b"0123456789abcdef" * 1300


class _Handler(BaseHTTPRequestHandler):
    hits = 0

    def do_GET(self):
        type(self).hits += 1
        if self.path == "/ok":
            body = PAYLOAD
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def log_message(self, format, *args):
        # 保持 pytest 输出干净：不打印每个请求的访问日志
        pass


@pytest.fixture
def server_base():
    _Handler.hits = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        thread.join()


@pytest.fixture(autouse=True)
def _no_proxy(monkeypatch):
    # 本地回环服务器不得经系统代理中转
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")


class TestDownloadResponse:

    def test_200_writes_file_with_exact_bytes(self, server_base, tmp_path):
        target = tmp_path / "out.bin"
        status = download_response(server_base + "/ok", str(target))
        assert status == 200
        assert target.read_bytes() == PAYLOAD

    def test_non_200_returns_status_and_writes_nothing(self, server_base,
                                                       tmp_path):
        target = tmp_path / "out.bin"
        status = download_response(server_base + "/missing", str(target))
        assert status == 404
        assert not target.exists()

    def test_existing_file_skipped_without_force(self, server_base, tmp_path):
        target = tmp_path / "out.bin"
        target.write_bytes(b"OLD")
        status = download_response(server_base + "/ok", str(target))
        assert status is None
        assert target.read_bytes() == b"OLD"
        assert _Handler.hits == 0

    def test_force_redownloads_existing_file(self, server_base, tmp_path):
        target = tmp_path / "out.bin"
        target.write_bytes(b"OLD")
        status = download_response(server_base + "/ok", str(target), force=True)
        assert status == 200
        assert target.read_bytes() == PAYLOAD

    def test_verbose_messages(self, server_base, tmp_path, capsys):
        target = tmp_path / "out.bin"

        download_response(server_base + "/ok", str(target), verbose=True)
        out = capsys.readouterr().out
        assert "Download completed successfully" in out

        target.write_bytes(b"OLD")
        download_response(server_base + "/ok", str(target), verbose=True)
        out = capsys.readouterr().out
        assert "already exists. Skipping download." in out
        assert target.read_bytes() == b"OLD"

    def test_missing_parent_raises_file_not_found(self, server_base,
                                                  tmp_path):
        target = tmp_path / "no" / "such" / "dir" / "out.bin"
        with pytest.raises(FileNotFoundError):
            download_response(server_base + "/ok", str(target))
