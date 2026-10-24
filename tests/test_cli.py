import os
from pathlib import Path

import pytest

from filelib.cli import main

# --- module-level helpers -------------------------------------------------
# _make_link_or_skip / _readlink_clean copied from tests/test_operator.py
# (repo style: standalone test files, no cross-file imports).


def _make_link_or_skip(link_path: Path, target: str, target_is_directory: bool = False) -> None:
    """Create a symlink, skipping on Windows without link privilege."""
    try:
        link_path.symlink_to(target, target_is_directory=target_is_directory)
    except OSError as exc:
        # Windows without symlink privilege (no admin or no developer
        # mode) commonly raises WinError 1314.
        if os.name == "nt" and getattr(exc, "winerror", None) == 1314:
            pytest.skip("Windows symlink requires admin/developer mode (WinError 1314)")
        raise


def _readlink_clean(link_path: Path) -> str:
    """os.readlink with the Windows ``\\?\\`` long-path prefix stripped."""
    return os.readlink(str(link_path)).removeprefix("\\\\?\\")


# Minimal synthetic PNG: signature + IHDR chunk (+ IEND chunk when
# complete); image_complete's strict check only requires the file to end
# with IEND, so no valid CRCs are needed (same fixtures as
# tests/test_identifier.py).
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_IHDR = b"\x00\x00\x00\x0dIHDR" + b"\x00" * 13 + b"\x00\x00\x00\x00"
PNG_IEND = b"\x00\x00\x00\x00IEND\xaeB\x60\x82"


def _write_png(path: Path, complete: bool = True) -> Path:
    path.write_bytes(PNG_SIGNATURE + PNG_IHDR + (PNG_IEND if complete else b""))
    return path


# --- copy -----------------------------------------------------------------


class TestCliCopy:
    """Tests for the `filelib copy` subcommand."""

    @pytest.fixture(autouse=True)
    def setup_tmpdir(self, tmp_path):
        self.src_dir = tmp_path / "src"
        self.dst_dir = tmp_path / "dst"
        self.src_dir.mkdir()
        self.dst_dir.mkdir()
        self.src_file = self.src_dir / "data.txt"
        self.src_file.write_text("source content")
        self.src_folder = self.src_dir / "folder"
        self.src_folder.mkdir()
        (self.src_folder / "inner.txt").write_text("inner")
        return

    def test_copy_file_success_returns_0(self, capsys):
        """复制文件：返回 0，内容一致，run-log 默认输出 Copied 行"""
        dst = self.dst_dir / "out.txt"

        rc = main(["copy", str(self.src_file), str(dst)])

        captured = capsys.readouterr()
        assert rc == 0
        assert dst.read_text() == "source content"
        assert "Copied" in captured.out

    def test_copy_directory_success(self):
        """复制目录：整个树被复制"""
        dst = self.dst_dir / "copied_folder"

        rc = main(["copy", str(self.src_folder), str(dst)])

        assert rc == 0
        assert (dst / "inner.txt").read_text() == "inner"

    def test_copy_relative_dst_bare_filename(self, monkeypatch):
        """Regression: 相对路径 dst 只有文件名（曾误报父目录不存在）"""
        monkeypatch.chdir(self.dst_dir)

        rc = main(["copy", str(self.src_file), "out.txt"])

        assert rc == 0
        assert (self.dst_dir / "out.txt").read_text() == "source content"

    def test_dry_run_previews_without_mutating(self, capsys):
        """--dry-run：输出 [dry-run] 前缀的预览行，不落盘"""
        dst = self.dst_dir / "out.txt"

        rc = main(["copy", str(self.src_file), str(dst), "--dry-run"])

        captured = capsys.readouterr()
        assert rc == 0
        assert "[dry-run] Copied" in captured.out
        assert not dst.exists()
        assert self.src_file.exists()

    def test_exist_policy_rename_with_rename_start_1(self):
        """--exist-policy rename --rename-start 1：目标占用时落到 data_1.txt"""
        dst = self.dst_dir / "data.txt"
        dst.write_text("occupied")

        rc = main(
            [
                "copy",
                str(self.src_file),
                str(dst),
                "--exist-policy",
                "rename",
                "--rename-start",
                "1",
            ]
        )

        assert rc == 0
        assert dst.read_text() == "occupied"
        assert (self.dst_dir / "data_1.txt").read_text() == "source content"

    def test_exist_policy_overwrite(self, capsys):
        """--exist-policy overwrite：先删已有文件再复制"""
        dst = self.dst_dir / "data.txt"
        dst.write_text("old")

        rc = main(["copy", str(self.src_file), str(dst), "--exist-policy", "overwrite"])

        captured = capsys.readouterr()
        assert rc == 0
        assert dst.read_text() == "source content"
        assert "Removed existing file" in captured.out

    def test_invalid_exist_policy_exits_2(self):
        """非法 --exist-policy：argparse 用法错误，SystemExit 2"""
        with pytest.raises(SystemExit) as excinfo:
            main(
                ["copy", str(self.src_file), str(self.dst_dir / "x.txt"), "--exist-policy", "bogus"]
            )
        assert excinfo.value.code == 2

    def test_make_dir_creates_missing_parents(self):
        """--make-dir：自动创建缺失的父目录"""
        dst = self.dst_dir / "deep" / "nested" / "out.txt"

        rc = main(["copy", str(self.src_file), str(dst), "--make-dir"])

        assert rc == 0
        assert dst.read_text() == "source content"

    def test_missing_parent_without_make_dir_returns_1(self, capsys):
        """缺父目录且未给 --make-dir：返回 1，stderr 报 Error，源文件完好"""
        dst = self.dst_dir / "missing" / "out.txt"

        rc = main(["copy", str(self.src_file), str(dst)])

        captured = capsys.readouterr()
        assert rc == 1
        assert captured.err.startswith("Error:")
        assert self.src_file.exists()

    def test_no_run_log_silences_output(self, capsys):
        """--no-run-log：成功复制但不打印任何内容"""
        dst = self.dst_dir / "out.txt"

        rc = main(["copy", str(self.src_file), str(dst), "--no-run-log"])

        captured = capsys.readouterr()
        assert rc == 0
        assert dst.read_text() == "source content"
        assert captured.out == ""

    def test_invalid_rename_format_returns_1(self, capsys):
        """--rename-format 无索引占位符：库抛 ValueError，返回 1"""
        dst = self.dst_dir / "data.txt"
        dst.write_text("occupied")

        rc = main(
            [
                "copy",
                str(self.src_file),
                str(dst),
                "--exist-policy",
                "rename",
                "--rename-format",
                "{stem}",
            ]
        )

        captured = capsys.readouterr()
        assert rc == 1
        assert captured.err.startswith("Error:")

    def test_negative_rename_start_returns_1(self, capsys):
        """负数 --rename-start：库抛 ValueError，返回 1"""
        dst = self.dst_dir / "data.txt"
        dst.write_text("occupied")

        rc = main(
            [
                "copy",
                str(self.src_file),
                str(dst),
                "--exist-policy",
                "rename",
                "--rename-start",
                "-1",
            ]
        )

        captured = capsys.readouterr()
        assert rc == 1
        assert captured.err.startswith("Error:")


class TestCliCopySymlinks:
    """Tests for `filelib copy` symlink flags (retarget implies preserve)."""

    @pytest.fixture(autouse=True)
    def setup_tree(self, tmp_path: Path) -> None:
        self.root = tmp_path / "link_root"
        self.root.mkdir()

        self.external = self.root / "external"
        self.external.mkdir()
        (self.external / "outside.txt").write_text("outside")

        self.src_dir = self.root / "src_dir"
        (self.src_dir / "sub").mkdir(parents=True)
        (self.src_dir / "real.txt").write_text("real")

        # absolute in-tree file link / dir link -> retargeted
        _make_link_or_skip(self.src_dir / "link_file", str(self.src_dir / "real.txt"))
        _make_link_or_skip(
            self.src_dir / "link_dir", str(self.src_dir / "sub"), target_is_directory=True
        )
        # outside / relative targets -> verbatim
        _make_link_or_skip(self.src_dir / "link_ext", str(self.external / "outside.txt"))
        _make_link_or_skip(self.src_dir / "link_rel", "real.txt")

        self.dst = self.root / "dst"
        return

    def test_retarget_implies_preserve(self, capsys):
        """只给 --retarget-symlinks：隐含 --preserve-symlinks，
        链接按链接复制且被重定向（不出现库的禁用 Warning）"""
        rc = main(["copy", str(self.src_dir), str(self.dst), "--retarget-symlinks"])

        captured = capsys.readouterr()
        assert rc == 0
        dst_link_file = self.dst / "link_file"
        dst_link_dir = self.dst / "link_dir"
        assert dst_link_file.is_symlink()
        assert dst_link_dir.is_symlink()
        assert os.path.normpath(_readlink_clean(dst_link_file)) == os.path.normpath(
            str(self.dst / "real.txt")
        )
        assert dst_link_dir.resolve() == (self.dst / "sub").resolve()
        assert "Warning:" not in captured.out
        assert "[RETARGET]" in captured.out

    def test_preserve_symlinks_keeps_links_without_retarget(self):
        """只给 --preserve-symlinks：保留链接，目标不变（仍指向源树）"""
        rc = main(["copy", str(self.src_dir), str(self.dst), "--preserve-symlinks"])

        assert rc == 0
        dst_link_file = self.dst / "link_file"
        assert dst_link_file.is_symlink()
        assert os.path.normpath(_readlink_clean(dst_link_file)) == os.path.normpath(
            str(self.src_dir / "real.txt")
        )

    def test_dry_run_previews_retarget_lines(self, capsys):
        """--dry-run + --retarget-symlinks：输出 [dry-run] [RETARGET] 预览，不落盘"""
        rc = main(["copy", str(self.src_dir), str(self.dst), "--retarget-symlinks", "--dry-run"])

        captured = capsys.readouterr()
        assert rc == 0
        assert "[dry-run] [RETARGET]" in captured.out
        assert not self.dst.exists()


# --- move -----------------------------------------------------------------


class TestCliMove:
    """Tests for the `filelib move` subcommand."""

    @pytest.fixture(autouse=True)
    def setup_tmpdir(self, tmp_path):
        self.src_dir = tmp_path / "src"
        self.dst_dir = tmp_path / "dst"
        self.src_dir.mkdir()
        self.dst_dir.mkdir()
        self.src_file = self.src_dir / "data.txt"
        self.src_file.write_text("source content")
        return

    def test_move_file_success(self, capsys):
        """移动文件：源消失、目标出现，run-log 默认输出 Moved 行"""
        dst = self.dst_dir / "moved.txt"

        rc = main(["move", str(self.src_file), str(dst)])

        captured = capsys.readouterr()
        assert rc == 0
        assert not self.src_file.exists()
        assert dst.read_text() == "source content"
        assert "Moved" in captured.out

    def test_dry_run_does_not_move(self, capsys):
        """--dry-run：只预览，源文件不动"""
        dst = self.dst_dir / "moved.txt"

        rc = main(["move", str(self.src_file), str(dst), "--dry-run"])

        captured = capsys.readouterr()
        assert rc == 0
        assert "[dry-run] Moved" in captured.out
        assert self.src_file.exists()
        assert not dst.exists()

    def test_exist_policy_rename_default_start(self):
        """--exist-policy rename（默认 start 0）：落到 blocker_0.txt"""
        dst = self.dst_dir / "blocker.txt"
        dst.write_text("occupied")

        rc = main(["move", str(self.src_file), str(dst), "--exist-policy", "rename"])

        assert rc == 0
        assert dst.read_text() == "occupied"
        assert (self.dst_dir / "blocker_0.txt").read_text() == "source content"
        assert not self.src_file.exists()

    def test_directory_onto_existing_file_returns_1(self, capsys):
        """目录移到已存在文件（default policy）：返回 1，源不动"""
        src_folder = self.src_dir / "folder"
        src_folder.mkdir()
        (src_folder / "inner.txt").write_text("inner")
        dst = self.dst_dir / "blocker.txt"
        dst.write_text("occupied")

        rc = main(["move", str(src_folder), str(dst)])

        captured = capsys.readouterr()
        assert rc == 1
        assert captured.err.startswith("Error:")
        assert (src_folder / "inner.txt").exists()
        assert dst.read_text() == "occupied"

    def test_retarget_symlinks_after_move(self):
        """--retarget-symlinks：移动后树内绝对链接被改指新位置"""
        src_folder = self.src_dir / "linked_tree"
        (src_folder / "sub").mkdir(parents=True)
        (src_folder / "real.txt").write_text("real")
        _make_link_or_skip(src_folder / "link_file", str(src_folder / "real.txt"))
        dst = self.dst_dir / "moved_tree"

        rc = main(["move", str(src_folder), str(dst), "--retarget-symlinks"])

        assert rc == 0
        moved_link = dst / "link_file"
        assert moved_link.is_symlink()
        assert os.path.normpath(_readlink_clean(moved_link)) == os.path.normpath(
            str(dst / "real.txt")
        )


# --- merge ----------------------------------------------------------------


class TestCliMerge:
    """Tests for the `filelib merge` subcommand."""

    @pytest.fixture(autouse=True)
    def setup_tree(self, tmp_path: Path) -> None:
        """Standard tree: expected merge result 2 copied, 1 skipped, 2 renamed
        (mirrors TestMergeFolders in tests/test_operator.py)."""
        self.src = tmp_path / "src"
        self.dst = tmp_path / "dst"
        self.src.mkdir()
        self.dst.mkdir()

        (self.src / "new_file.txt").write_text("brand new")
        (self.src / "same.txt").write_text("same content")
        (self.dst / "same.txt").write_text("same content")
        (self.src / "diff.txt").write_text("source version")
        (self.dst / "diff.txt").write_text("target version")
        (self.src / "as_dir.txt").write_text("source as dir")
        (self.dst / "as_dir.txt").mkdir()
        # nested/deep.txt: parent directory must be created in dst
        (self.src / "nested").mkdir()
        (self.src / "nested" / "deep.txt").write_text("deep")
        # empty_dir: must not be created in dst; extra.txt: only in dst
        (self.src / "empty_dir").mkdir()
        (self.dst / "extra.txt").write_text("target only")
        return

    def test_merge_success_prints_summary(self, capsys):
        """合并成功：返回 0，打印精确的 Summary 行"""
        rc = main(["merge", str(self.src), str(self.dst)])

        captured = capsys.readouterr()
        assert rc == 0
        assert "Summary: 2 copied, 1 skipped, 2 renamed" in captured.out
        assert (self.dst / "new_file.txt").read_text() == "brand new"
        assert (self.dst / "diff.txt").read_text() == "target version"
        assert (self.dst / "diff_0.txt").read_text() == "source version"

    def test_dry_run_leaves_dst_untouched_but_stats_exact(self, capsys):
        """--dry-run：dst 不变，但 Summary 仍是精确预览"""
        rc = main(["merge", str(self.src), str(self.dst), "--dry-run"])

        captured = capsys.readouterr()
        assert rc == 0
        assert not (self.dst / "new_file.txt").exists()
        assert "Summary: 2 copied, 1 skipped, 2 renamed" in captured.out

    def test_custom_rename_format(self):
        """--rename-format '{stem} ({i}){suffix}'：冲突文件落到 diff (0).txt"""
        rc = main(
            ["merge", str(self.src), str(self.dst), "--rename-format", "{stem} ({i}){suffix}"]
        )

        assert rc == 0
        assert (self.dst / "diff (0).txt").read_text() == "source version"

    def test_same_folder_returns_1(self, capsys):
        """src 与 dst 相同：返回 1"""
        rc = main(["merge", str(self.src), str(self.src)])

        captured = capsys.readouterr()
        assert rc == 1
        assert captured.err.startswith("Error:")

    def test_dst_inside_src_returns_1(self, capsys):
        """dst 嵌套在 src 内：返回 1"""
        nested = self.src / "nested_dst"
        nested.mkdir()

        rc = main(["merge", str(self.src), str(nested)])

        captured = capsys.readouterr()
        assert rc == 1
        assert captured.err.startswith("Error:")

    def test_missing_src_returns_1(self, capsys):
        """src 不存在：返回 1，stderr 报 FileNotFoundError"""
        rc = main(["merge", str(self.src / "nope"), str(self.dst)])

        captured = capsys.readouterr()
        assert rc == 1
        assert captured.err.startswith("Error:")
        assert "not found" in captured.err.lower()


# --- check-image ----------------------------------------------------------


class TestCliCheckImage:
    """Tests for the `filelib check-image` subcommand."""

    @pytest.fixture(autouse=True)
    def setup_tmpdir(self, tmp_path):
        self.complete_png = _write_png(tmp_path / "complete.png", complete=True)
        self.truncated_png = _write_png(tmp_path / "truncated.png", complete=False)
        self.notes_txt = tmp_path / "notes.txt"
        self.notes_txt.write_text("hello")
        return

    def test_complete_png_ok_returns_0(self, capsys):
        """完整 PNG：输出 ok，返回 0"""
        rc = main(["check-image", str(self.complete_png)])

        captured = capsys.readouterr()
        assert rc == 0
        assert f"{self.complete_png}: ok" in captured.out
        assert "Summary: 1 files: 1 ok" in captured.out

    def test_truncated_png_corrupted_returns_1(self, capsys):
        """截断 PNG：输出 corrupted，返回 1"""
        rc = main(["check-image", str(self.truncated_png)])

        captured = capsys.readouterr()
        assert rc == 1
        assert f"{self.truncated_png}: corrupted" in captured.out

    def test_extension_method_unsupported_txt_returns_0(self, capsys):
        """--mime-method extension 对 .txt：输出 unsupported，不影响退出码"""
        rc = main(["check-image", str(self.notes_txt), "--mime-method", "extension"])

        captured = capsys.readouterr()
        assert rc == 0
        assert f"{self.notes_txt}: unsupported" in captured.out

    def test_empty_file_reports_error_and_continues(self, capsys):
        """空文件（magic 无法识别 -> PureError）：stderr 报 Error，继续检查其余文件"""
        empty = self.notes_txt.parent / "empty.bin"
        empty.write_bytes(b"")

        rc = main(["check-image", str(empty), str(self.complete_png)])

        captured = capsys.readouterr()
        assert rc == 1
        assert captured.err.startswith("Error:")
        assert str(empty) in captured.err
        # 第二个文件仍被检查并报告
        assert f"{self.complete_png}: ok" in captured.out
        assert "1 errors" in captured.out

    def test_unidentifiable_content_reports_error(self, capsys):
        """非空但无法识别的内容（PureError）：stderr 报 Error 并计入 errors"""
        junk = self.notes_txt.parent / "junk.bin"
        junk.write_bytes(b"\r\n")

        rc = main(["check-image", str(junk)])

        captured = capsys.readouterr()
        assert rc == 1
        assert str(junk) in captured.err
        assert "Summary: 1 files: 0 ok, 0 corrupted, 0 unsupported, 1 errors" in captured.out

    def test_missing_file_in_batch_reports_rest(self, capsys):
        """批量中含缺失文件：其余文件仍被报告，返回 1"""
        missing = self.notes_txt.parent / "gone.png"

        rc = main(["check-image", str(missing), str(self.truncated_png)])

        captured = capsys.readouterr()
        assert rc == 1
        assert captured.err.startswith("Error:")
        assert f"{self.truncated_png}: corrupted" in captured.out

    def test_mixed_batch_summary_line(self, capsys):
        """混合批次：ok/corrupted/unsupported 各一行 + Summary 行"""
        rc = main(
            [
                "check-image",
                str(self.complete_png),
                str(self.truncated_png),
                str(self.notes_txt),
                "--mime-method",
                "magic",
            ]
        )

        captured = capsys.readouterr()
        assert rc == 1
        assert ": ok" in captured.out
        assert ": corrupted" in captured.out
        assert ": unsupported" in captured.out
        assert "Summary: 3 files: 1 ok, 1 corrupted, 1 unsupported, 0 errors" in captured.out

    def test_invalid_mime_method_exits_2(self):
        """非法 --mime-method：argparse 用法错误，SystemExit 2"""
        with pytest.raises(SystemExit) as excinfo:
            main(["check-image", str(self.complete_png), "--mime-method", "bogus"])
        assert excinfo.value.code == 2


# --- main / parser --------------------------------------------------------


class TestCliMain:
    """Tests for main() dispatch and argparse behavior."""

    def test_no_arguments_exits_2(self):
        """无参数：用法错误，SystemExit 2"""
        with pytest.raises(SystemExit) as excinfo:
            main([])
        assert excinfo.value.code == 2

    def test_unknown_subcommand_exits_2(self):
        """未知子命令：用法错误，SystemExit 2"""
        with pytest.raises(SystemExit) as excinfo:
            main(["frobnicate"])
        assert excinfo.value.code == 2

    def test_version_exits_0(self, capsys):
        """--version：SystemExit 0，stdout 以 filelib 开头"""
        with pytest.raises(SystemExit) as excinfo:
            main(["--version"])
        assert excinfo.value.code == 0

        captured = capsys.readouterr()
        assert captured.out.startswith("filelib")
