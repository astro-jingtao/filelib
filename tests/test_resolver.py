import os
from pathlib import Path

import pytest

from filelib.resolver import is_same_path


def _create_file_symlink(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target)
    except OSError as exc:
        # Windows without symlink privilege (no admin or no developer mode)
        # commonly raises WinError 1314.
        if os.name == "nt" and getattr(exc, "winerror", None) == 1314:
            pytest.skip("Windows symlink requires admin/developer mode (WinError 1314)")
        raise


class TestIsSamePath:

    def test_identical_strings_are_same(self, tmp_path):
        target = tmp_path / "a.txt"
        target.write_text("data")
        assert is_same_path(str(target), str(target)) is True

    def test_path_object_accepted(self, tmp_path):
        target = tmp_path / "a.txt"
        target.write_text("data")
        assert is_same_path(target, str(target)) is True

    def test_redundant_dot_segment_resolves_same(self, tmp_path):
        target = tmp_path / "a.txt"
        target.write_text("data")
        spelled = os.path.join(str(tmp_path), ".", "a.txt")
        assert is_same_path(spelled, str(target)) is True

    def test_double_separator_resolves_same(self, tmp_path):
        target = tmp_path / "a.txt"
        target.write_text("data")
        spelled = str(tmp_path) + os.sep + os.sep + "a.txt"
        assert is_same_path(spelled, str(target)) is True

    def test_relative_spelling_matches_absolute(self, tmp_path,
                                                monkeypatch):
        target = tmp_path / "a.txt"
        target.write_text("data")
        monkeypatch.chdir(tmp_path)
        assert is_same_path("a.txt", str(target)) is True

    def test_different_files_are_not_same(self, tmp_path):
        one = tmp_path / "a.txt"
        other = tmp_path / "b.txt"
        one.write_text("data")
        other.write_text("data")
        assert is_same_path(str(one), str(other)) is False

    def test_nonexistent_paths_compare_by_resolved_spelling(self, tmp_path):
        # resolve() 非 strict：不存在的路径也能解析出规范形式参与比较
        one = str(tmp_path / "nope1")
        assert is_same_path(one, one) is True
        assert is_same_path(one, str(tmp_path / "nope2")) is False

    def test_symlink_resolves_to_target(self, tmp_path):
        target = tmp_path / "a.txt"
        target.write_text("data")
        link = tmp_path / "link.txt"
        _create_file_symlink(link, target)
        assert is_same_path(str(link), str(target)) is True
