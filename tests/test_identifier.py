import pytest
from pathlib import Path

from filelib.identifier import is_file_corrupted

# Minimal synthetic PNG: signature + IHDR chunk (+ IEND chunk when
# complete). image_complete's strict PNG check only requires the file to
# end with the IEND chunk, so no valid CRCs are needed.
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
PNG_IHDR = b'\x00\x00\x00\x0dIHDR' + b'\x00' * 13 + b'\x00\x00\x00\x00'
PNG_IEND = b'\x00\x00\x00\x00IEND\xaeB\x60\x82'


def _write_png(path: Path, complete: bool = True) -> Path:
    path.write_bytes(PNG_SIGNATURE + PNG_IHDR
                     + (PNG_IEND if complete else b''))
    return path


class TestIsFileCorrupted:
    """Tests for identifier.is_file_corrupted."""

    @pytest.fixture(autouse=True)
    def setup_tmpdir(self, tmp_path):
        self.complete_png = _write_png(tmp_path / "complete.png", complete=True)
        self.truncated_png = _write_png(tmp_path / "truncated.png", complete=False)
        self.notes_txt = tmp_path / "notes.txt"
        self.notes_txt.write_text("hello")
        yield

    def test_complete_png_str_path_not_corrupted(self):
        """完整 PNG（str 路径）：not corrupted"""
        assert is_file_corrupted(str(self.complete_png)) is False

    def test_complete_png_path_object_not_corrupted(self, capsys):
        """Regression: Path 输入同样判定完整

        image_complete.load() 不接受 Path（曾导致误报 corrupted
        并打印 'Unhandled data type'）。"""
        assert is_file_corrupted(self.complete_png) is False

        captured = capsys.readouterr()
        assert "Unhandled data type" not in captured.out

    def test_truncated_png_corrupted(self):
        """截断 PNG（缺 IEND）：corrupted"""
        assert is_file_corrupted(str(self.truncated_png)) is True

    def test_unsupported_mime_returns_none_by_default(self):
        """不支持的 MIME（text/plain）：默认返回 None"""
        assert is_file_corrupted(str(self.notes_txt)) is None

    def test_unsupported_mime_extension_method_returns_none(self):
        """extension 模式下未知后缀：返回 None 而非抛错"""
        assert is_file_corrupted(str(self.notes_txt),
                                 mime_method='extension') is None

    def test_unsupported_policy_raise_raises(self):
        """unsupported_policy='raise'：抛 ValueError"""
        with pytest.raises(ValueError, match="Unsupported MIME type"):
            is_file_corrupted(str(self.notes_txt),
                              unsupported_policy='raise')

    def test_invalid_mime_method_raises(self):
        """非法 mime_method：抛 ValueError"""
        with pytest.raises(ValueError, match="Invalid mime_method"):
            is_file_corrupted(str(self.complete_png), mime_method='bogus')

    def test_explicit_mime_skips_detection(self):
        """显式传入 mime：跳过探测，直接按该 MIME 检查"""
        # text/plain 不在受支持列表中 -> None，证明没有走文件探测
        assert is_file_corrupted(str(self.complete_png),
                                 mime='text/plain') is None
