from pathlib import Path
import os

import pytest

from filelib.scanner import is_empty_dir, ls


def _create_dir_symlink(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        # Windows without symlink privilege (no admin or no developer mode)
        # commonly raises WinError 1314.
        if os.name == "nt" and getattr(exc, "winerror", None) == 1314:
            pytest.skip("Windows symlink requires admin/developer mode (WinError 1314)")
        raise


def _prepare_symlink_tree(tmp_path: Path) -> Path:
    root = tmp_path / "scan_root"
    real_dir = root / "real"
    nested = real_dir / "sub"
    nested.mkdir(parents=True)
    (nested / "data.txt").write_text("hello")

    symlink_dir = root / "link_to_real"
    symlink_dir.parent.mkdir(parents=True, exist_ok=True)
    _create_dir_symlink(symlink_dir, real_dir)
    return root


class TestLs:

    @pytest.fixture(autouse=True)
    def setup_tmpdir(self, tmp_path: Path) -> None:
        self.root = _prepare_symlink_tree(tmp_path)

    def test_ls_recursive_default_follows_directory_symlink(self) -> None:
        files = ls(directory=str(self.root),
                   recursive=True,
                   path_type="rel_path")
        normalized = [Path(path).as_posix() for path in files]

        assert normalized == ["link_to_real/sub/data.txt", "real/sub/data.txt"]

    def test_ls_recursive_follow_symlinks_false_skips_symlinked_path(
            self) -> None:
        files = ls(
            directory=str(self.root),
            recursive=True,
            path_type="rel_path",
            follow_symlinks=False,
        )
        normalized = [Path(path).as_posix() for path in files]

        assert normalized == ["real/sub/data.txt"]


class TestLsOnDuplicates:
    """on_duplicates 三个合法取值的行为与非法值的入口校验。"""

    @pytest.fixture(autouse=True)
    def setup_tmpdir(self, tmp_path: Path) -> None:
        # 两个子目录各有一个同名文件：file_only 模式下产生重复名
        self.root = tmp_path / "dup_root"
        (self.root / "sub1").mkdir(parents=True)
        (self.root / "sub2").mkdir(parents=True)
        (self.root / "sub1" / "data.txt").write_text("a")
        (self.root / "sub2" / "data.txt").write_text("b")

    def test_raise_mode_raises_on_duplicate_names(self) -> None:
        with pytest.raises(ValueError, match="Duplicate file names"):
            ls(str(self.root), recursive=True, path_type="file_only")

    def test_warn_mode_warns_and_returns_result(self) -> None:
        with pytest.warns(UserWarning, match="Duplicate file names"):
            result = ls(str(self.root), recursive=True,
                        path_type="file_only", on_duplicates="warn")
        assert result == ["data.txt", "data.txt"]

    def test_ignore_mode_returns_duplicates(self) -> None:
        result = ls(str(self.root), recursive=True,
                    path_type="file_only", on_duplicates="ignore")
        assert result == ["data.txt", "data.txt"]

    def test_invalid_on_duplicates_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="on_duplicates"):
            ls(str(self.root), recursive=True, on_duplicates="bogus")

    def test_invalid_on_duplicates_rejected_without_duplicates(self) -> None:
        # 非法值在入口即拒绝：即使不产生重复名、非 file_only 模式也可见
        with pytest.raises(ValueError, match="on_duplicates"):
            ls(str(self.root), path_type="abs_full_path", on_duplicates="")

    def test_invalid_path_type_raises_value_error(self) -> None:
        # path_type 的校验是惰性的：在遍历中遇到第一个文件时才抛出
        with pytest.raises(ValueError, match="path_type"):
            ls(str(self.root), recursive=True, path_type="bogus")


class TestIsEmptyDir:

    @pytest.fixture(autouse=True)
    def setup_tmpdir(self, tmp_path: Path) -> None:
        self.root = tmp_path / "empty_check"
        self.root.mkdir()
        self.empty_dir = self.root / "empty"
        self.empty_dir.mkdir()

    # 浅层模式（默认）：任何条目（文件/子目录/隐藏文件）都算内容

    def test_empty_dir_returns_true(self) -> None:
        assert is_empty_dir(str(self.empty_dir)) is True

    def test_dir_with_file_returns_false(self) -> None:
        (self.empty_dir / "file.txt").write_text("data")
        assert is_empty_dir(str(self.empty_dir)) is False

    def test_dir_with_only_empty_subdir_returns_false(self) -> None:
        (self.empty_dir / "sub").mkdir()
        assert is_empty_dir(str(self.empty_dir)) is False

    def test_dir_with_hidden_file_returns_false(self) -> None:
        (self.empty_dir / ".hidden").write_text("data")
        assert is_empty_dir(str(self.empty_dir)) is False

    # recursive 模式：整棵子树无任何文件才算空（只含空子目录算空）

    def test_recursive_empty_dir_returns_true(self) -> None:
        assert is_empty_dir(str(self.empty_dir), recursive=True) is True

    def test_recursive_nested_empty_subdirs_returns_true(self) -> None:
        (self.empty_dir / "a" / "b" / "c").mkdir(parents=True)
        assert is_empty_dir(str(self.empty_dir), recursive=True) is True

    def test_recursive_top_level_file_returns_false(self) -> None:
        (self.empty_dir / "file.txt").write_text("data")
        assert is_empty_dir(str(self.empty_dir), recursive=True) is False

    def test_recursive_deep_file_returns_false(self) -> None:
        (self.empty_dir / "a" / "b").mkdir(parents=True)
        (self.empty_dir / "a" / "b" / "file.txt").write_text("data")
        assert is_empty_dir(str(self.empty_dir), recursive=True) is False

    def test_recursive_follows_directory_symlink_to_files(self) -> None:
        target = self.root / "outside"
        target.mkdir()
        (target / "file.txt").write_text("data")
        _create_dir_symlink(self.empty_dir / "link_to_outside", target)
        assert is_empty_dir(str(self.empty_dir), recursive=True) is False

    # 入参与异常

    def test_pathlib_path_accepted(self) -> None:
        assert is_empty_dir(self.empty_dir) is True

    def test_missing_path_raises_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            is_empty_dir(str(self.root / "nope"))

    def test_missing_path_recursive_raises_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            is_empty_dir(str(self.root / "nope"), recursive=True)

    def test_file_path_raises_not_a_directory(self) -> None:
        file_path = self.root / "plain.txt"
        file_path.write_text("data")
        with pytest.raises(NotADirectoryError):
            is_empty_dir(str(file_path))
