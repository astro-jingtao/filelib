from pathlib import Path

import pytest

from filelib.scanner import ls


def _prepare_symlink_tree(tmp_path: Path) -> Path:
    root = tmp_path / "scan_root"
    real_dir = root / "real"
    nested = real_dir / "sub"
    nested.mkdir(parents=True)
    (nested / "data.txt").write_text("hello")

    symlink_dir = root / "link_to_real"
    symlink_dir.parent.mkdir(parents=True, exist_ok=True)
    symlink_dir.symlink_to(real_dir, target_is_directory=True)
    return root


class TestLs:

    @pytest.fixture(autouse=True)
    def setup_tmpdir(self, tmp_path: Path) -> None:
        self.root = _prepare_symlink_tree(tmp_path)

    def test_ls_recursive_default_follows_directory_symlink(self) -> None:
        files = ls(directory=str(self.root),
                   recursive=True,
                   path_type="rel_path")

        assert files == ["link_to_real/sub/data.txt", "real/sub/data.txt"]

    def test_ls_recursive_follow_symlinks_false_skips_symlinked_path(
            self) -> None:
        files = ls(
            directory=str(self.root),
            recursive=True,
            path_type="rel_path",
            follow_symlinks=False,
        )

        assert files == ["real/sub/data.txt"]
