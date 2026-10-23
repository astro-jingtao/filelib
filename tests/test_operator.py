# pylint: disable=attribute-defined-outside-init

import os
from pathlib import Path
import shutil

import pytest

import filelib.operator as operator_module
from filelib.operator import copy, dry_run_session, get_unique_new_dst, merge_folders, move, remove


class TestRemove:

    # ===== Fixtures: 准备测试环境 =====

    @pytest.fixture(autouse=True)
    def setup_tmpdir(self, tmp_path):
        """
        每个测试用例执行前创建一个临时的测试目录，执行后自动清理。
        pytest 内置的 tmp_path fixture 会处理临时目录的创建和清理。
        """
        self.test_dir = tmp_path / "test_root"
        self.test_dir.mkdir()

        # 创建一些通用的测试文件结构
        # 文件: test_root/file.txt
        self.file_path = self.test_dir / "file.txt"
        self.file_path.write_text("content")

        # 空文件夹: test_root/empty_dir
        self.empty_dir_path = self.test_dir / "empty_dir"
        self.empty_dir_path.mkdir()

        # 非空文件夹: test_root/non_empty_dir
        self.non_empty_dir_path = self.test_dir / "non_empty_dir"
        self.non_empty_dir_path.mkdir()
        (self.non_empty_dir_path /
         "inner_file.txt").write_text("inner content")

        yield

    # ===== 测试用例 =====

    def test_remove_file_success(self):
        """测试删除文件：成功删除"""
        assert self.file_path.exists()
        remove(str(self.file_path))
        assert not self.file_path.exists()

    def test_remove_empty_dir_success(self):
        """测试删除空文件夹：默认参数下成功删除"""
        assert self.empty_dir_path.exists()
        remove(str(self.empty_dir_path))
        assert not self.empty_dir_path.exists()

    def test_remove_non_empty_dir_recursive_true(self):
        """测试非空文件夹：recursive=True，递归删除"""
        assert self.non_empty_dir_path.exists()
        remove(str(self.non_empty_dir_path), recursive=True)
        assert not self.non_empty_dir_path.exists()

    def test_remove_non_empty_dir_recursive_false_raises_error(self):
        """测试非空文件夹：recursive=False (默认)，抛出 OSError"""
        with pytest.raises(OSError) as excinfo:
            remove(str(self.non_empty_dir_path), recursive=False)

        assert "Directory not empty" in str(excinfo.value)
        # 确保文件没有被删除
        assert self.non_empty_dir_path.exists()

        # 应该是默认行为
        with pytest.raises(OSError) as excinfo:
            remove(str(self.non_empty_dir_path))

        assert "Directory not empty" in str(excinfo.value)
        # 确保文件没有被删除
        assert self.non_empty_dir_path.exists()

    def test_remove_non_empty_dir_recursive_skip(self, capsys):
        """测试非空文件夹：recursive='skip'，跳过删除并打印日志"""
        remove(str(self.non_empty_dir_path), recursive='skip')

        captured = capsys.readouterr()
        # 当前实现在非 dry_run 时没有打印跳过日志，所以这里主要验证文件还在
        # 如果你的实现里加了这个打印，可以取消下面注释
        # assert "Skip non-empty directory" in captured.out

        # 关键断言：文件夹应该依然存在
        assert self.non_empty_dir_path.exists()

    def test_remove_non_existing_path(self, capsys):
        """测试不存在的路径：打印警告并不报错"""
        fake_path = str(self.test_dir / "ghost.txt")
        remove(fake_path)

        captured = capsys.readouterr()
        assert "Warning: Path does not exist" in captured.out

    # ===== Dry Run 测试 =====

    def test_dry_run_file(self, capsys):
        """测试 Dry Run：文件不删除，仅打印"""
        remove(str(self.file_path), dry_run=True)

        captured = capsys.readouterr()
        assert "[dry-run] Removed file" in captured.out
        assert self.file_path.exists()  # 文件应该还在

    def test_dry_run_empty_dir(self, capsys):
        """测试 Dry Run：空文件夹不删除，仅打印"""
        remove(str(self.empty_dir_path), dry_run=True)

        captured = capsys.readouterr()
        assert "[dry-run] Removed empty directory" in captured.out
        assert self.empty_dir_path.exists()

    def test_dry_run_non_empty_dir_recursive_true(self, capsys):
        """测试 Dry Run：非空文件夹，recursive=True 模式"""
        remove(str(self.non_empty_dir_path), recursive=True, dry_run=True)

        captured = capsys.readouterr()
        assert "[dry-run] Removed directory" in captured.out
        assert self.non_empty_dir_path.exists()

    def test_dry_run_non_empty_dir_recursive_skip(self, capsys):
        """测试 Dry Run：非空文件夹，recursive='skip' 模式，应打印跳过日志"""
        remove(str(self.non_empty_dir_path), recursive='skip', dry_run=True)

        captured = capsys.readouterr()
        assert "[dry-run] Skipped non-empty directory" in captured.out
        assert self.non_empty_dir_path.exists()

    # ===== Run Log 测试 =====

    def test_run_log_file(self, capsys):
        """测试 run_log：删除文件时打印执行日志"""
        remove(str(self.file_path), run_log=True)

        captured = capsys.readouterr()
        assert "Removed file" in captured.out
        assert "[dry-run]" not in captured.out
        assert not self.file_path.exists()

    def test_run_log_empty_dir(self, capsys):
        """测试 run_log：删除空文件夹时打印执行日志"""
        remove(str(self.empty_dir_path), run_log=True)

        captured = capsys.readouterr()
        assert "Removed empty directory" in captured.out
        assert "[dry-run]" not in captured.out
        assert not self.empty_dir_path.exists()

    def test_run_log_non_empty_dir_recursive_true(self, capsys):
        """测试 run_log：非空文件夹 recursive=True 时打印执行日志"""
        remove(str(self.non_empty_dir_path), recursive=True, run_log=True)

        captured = capsys.readouterr()
        assert "Removed directory" in captured.out
        assert "[dry-run]" not in captured.out
        assert not self.non_empty_dir_path.exists()

    def test_run_log_non_empty_dir_recursive_skip(self, capsys):
        """测试 run_log：非空文件夹 recursive='skip' 时打印跳过日志"""
        remove(str(self.non_empty_dir_path), recursive='skip', run_log=True)

        captured = capsys.readouterr()
        assert "Skipped non-empty directory" in captured.out
        assert "[dry-run]" not in captured.out
        assert self.non_empty_dir_path.exists()

    def test_run_log_with_dry_run_prints_dry_run_only(self, capsys):
        """测试 run_log + dry_run：只输出 dry-run 日志，不输出普通 run_log"""
        remove(str(self.file_path), run_log=True, dry_run=True)

        captured = capsys.readouterr()
        assert "[dry-run] Removed file" in captured.out
        assert "\nRemoved file" not in captured.out
        assert self.file_path.exists()


class TestMove:

    @pytest.fixture(autouse=True)
    def setup_tmpdir(self, tmp_path):
        self.test_dir = tmp_path / "move_root"
        self.test_dir.mkdir()

        self.src_dir = self.test_dir / "src"
        self.src_dir.mkdir()

        self.dst_dir = self.test_dir / "dst"
        self.dst_dir.mkdir()

        self.src_file = self.src_dir / "source.txt"
        self.src_file.write_text("source content")

        yield

    def test_move_to_file_path_success(self):
        """默认移动到目标文件路径：成功移动"""
        dst_file = self.dst_dir / "moved.txt"

        move(str(self.src_file), str(dst_file))

        assert not self.src_file.exists()
        assert dst_file.exists()
        assert dst_file.read_text() == "source content"

    def test_move_to_existing_directory_success(self):
        """目标为已有目录：移动后文件进入该目录"""
        move(str(self.src_file), str(self.dst_dir))

        moved_file = self.dst_dir / self.src_file.name
        assert not self.src_file.exists()
        assert moved_file.exists()
        assert moved_file.read_text() == "source content"

    def test_move_file_to_existing_file_default_overwrites(self):
        """Docstring (move, table): file src + existing file dst +
        exist_policy='default' -> overwritten (shutil.move's copy2
        fallback; os.rename cannot replace on Windows)."""
        dst_file = self.dst_dir / "source.txt"
        dst_file.write_text("old content")

        move(str(self.src_file), str(dst_file))

        assert dst_file.read_text() == "source content"
        assert not self.src_file.exists()

    def test_move_directory_success(self):
        """Docstring (move, table): directory src + missing dst ->
        whole tree moved."""
        dst = self.test_dir / "moved_folder"

        move(str(self.src_dir), str(dst))

        assert not self.src_dir.exists()
        assert (dst / "source.txt").read_text() == "source content"

    def test_move_directory_to_existing_dir_lands_inside(self):
        """Docstring (move, table): directory src + existing dir dst ->
        tree lands at dst/<basename(src)>."""
        dst = self.test_dir / "container"
        dst.mkdir()

        move(str(self.src_dir), str(dst))

        assert (dst / "src" / "source.txt").read_text() == "source content"

    def test_move_directory_to_existing_dir_conflict_raises_shutil_error(self):
        """Docstring (move, Raises): dst is an existing directory and
        dst/<basename(src)> already exists -> shutil.Error."""
        dst = self.test_dir / "container"
        (dst / "src").mkdir(parents=True)

        with pytest.raises(shutil.Error):
            move(str(self.src_dir), str(dst))

    def test_move_directory_to_existing_file_default_raises(self):
        """Docstring (move, table): directory src + existing file dst +
        'default' -> FileExistsError, source untouched."""
        dst = self.test_dir / "blocker.txt"
        dst.write_text("block")

        with pytest.raises(FileExistsError):
            move(str(self.src_dir), str(dst))

        assert self.src_file.exists()

    def test_move_directory_to_existing_file_overwrite(self):
        """Docstring (move, table): directory src + existing file dst +
        'overwrite' -> file removed first, then tree moved."""
        dst = self.test_dir / "blocker.txt"
        dst.write_text("block")

        move(str(self.src_dir), str(dst), exist_policy='overwrite')

        assert dst.is_dir()
        assert (dst / "source.txt").read_text() == "source content"

    def test_move_directory_to_existing_file_rename(self):
        """Docstring (move, table): directory src + existing file dst +
        'rename' -> tree moved to stem_0.ext."""
        dst = self.test_dir / "blocker.txt"
        dst.write_text("block")

        move(str(self.src_dir), str(dst), exist_policy='rename')

        assert dst.read_text() == "block"
        assert (self.test_dir / "blocker_0.txt" / "source.txt").is_file()

    def test_move_make_dir_true_creates_parent(self):
        """make_dir=True 时自动创建父目录并移动"""
        dst_file = self.test_dir / "new_parent" / "deep" / "moved.txt"

        move(str(self.src_file), str(dst_file), make_dir=True)

        assert not self.src_file.exists()
        assert dst_file.exists()
        assert dst_file.read_text() == "source content"

    def test_move_make_dir_false_raises(self):
        """make_dir=False 且目标父目录不存在：抛出 FileNotFoundError"""
        dst_file = self.test_dir / "new_parent" / "deep" / "moved.txt"

        with pytest.raises(FileNotFoundError) as excinfo:
            move(str(self.src_file), str(dst_file), make_dir=False)

        assert "does not exist" in str(excinfo.value)
        assert self.src_file.exists()

    def test_move_exist_policy_overwrite(self):
        """exist_policy='overwrite'：先删除目标再移动"""
        dst_file = self.dst_dir / "target.txt"
        dst_file.write_text("old content")

        move(str(self.src_file), str(dst_file), exist_policy='overwrite')

        assert not self.src_file.exists()
        assert dst_file.exists()
        assert dst_file.read_text() == "source content"

    def test_move_exist_policy_rename(self):
        """exist_policy='rename'：目标已存在时自动改名"""
        dst_file = self.dst_dir / "target.txt"
        dst_file.write_text("old content")

        # 占用 _0，验证会继续尝试 _1
        renamed_0 = self.dst_dir / "target_0.txt"
        renamed_0.write_text("occupied")

        move(str(self.src_file), str(dst_file), exist_policy='rename')

        renamed_1 = self.dst_dir / "target_1.txt"
        assert not self.src_file.exists()
        assert dst_file.read_text() == "old content"
        assert renamed_0.read_text() == "occupied"
        assert renamed_1.exists()
        assert renamed_1.read_text() == "source content"

    def test_move_exist_policy_invalid_raises(self):
        """非法 exist_policy：抛出 ValueError"""
        dst_file = self.dst_dir / "target.txt"
        dst_file.write_text("old content")

        with pytest.raises(ValueError) as excinfo:
            move(str(self.src_file), str(dst_file), exist_policy='invalid')

        assert "exist_policy must be" in str(excinfo.value)
        assert self.src_file.exists()

    def test_move_exist_policy_rename_custom_format(self):
        """exist_policy='rename' + 自定义 rename_format：按模板生成新名"""
        dst_file = self.dst_dir / "target.txt"
        dst_file.write_text("old content")

        move(str(self.src_file), str(dst_file), exist_policy='rename',
             rename_format='{i:02d}_{stem}{suffix}')

        renamed = self.dst_dir / "00_target.txt"
        assert not self.src_file.exists()
        assert dst_file.read_text() == "old content"
        assert renamed.read_text() == "source content"

    def test_move_rename_invalid_format_raises_in_dry_run(self):
        """dry_run + 非法 rename_format：预览阶段即抛 ValueError"""
        dst_file = self.dst_dir / "target.txt"
        dst_file.write_text("old content")

        with pytest.raises(ValueError, match="Invalid rename_format"):
            move(str(self.src_file), str(dst_file), dry_run=True,
                 exist_policy='rename', rename_format='{oops}')

        assert self.src_file.exists()
        assert dst_file.read_text() == "old content"

    def test_move_dry_run_no_fs_change(self, capsys):
        """dry_run=True：不执行真实移动，但输出 dry-run 日志"""
        dst_file = self.dst_dir / "dry_moved.txt"

        move(str(self.src_file), str(dst_file), dry_run=True)

        captured = capsys.readouterr()
        assert "[dry-run] Moved" in captured.out
        assert self.src_file.exists()
        assert not dst_file.exists()

    def test_move_dry_run_overwrite_keeps_destination(self, capsys):
        """dry_run + overwrite：不删除原目标文件"""
        dst_file = self.dst_dir / "target.txt"
        dst_file.write_text("old content")

        move(str(self.src_file),
             str(dst_file),
             dry_run=True,
             exist_policy='overwrite')

        captured = capsys.readouterr()
        assert "[dry-run] Removed existing file" in captured.out
        assert "[dry-run] Moved" in captured.out
        assert self.src_file.exists()
        assert dst_file.read_text() == "old content"

    def test_move_run_log_prints_log(self, capsys):
        """run_log=True：输出执行日志（非 dry-run）"""
        dst_file = self.dst_dir / "runlog.txt"

        move(str(self.src_file), str(dst_file), run_log=True)

        captured = capsys.readouterr()
        assert "Moved" in captured.out
        assert "[dry-run]" not in captured.out

    def test_move_run_log_with_make_dir_prints_create(self, capsys):
        """run_log=True + make_dir=True：打印创建目录日志"""
        dst_file = self.test_dir / "new_parent" / "deep" / "runlog.txt"

        move(str(self.src_file), str(dst_file), make_dir=True, run_log=True)

        captured = capsys.readouterr()
        assert "Create directory" in captured.out
        assert "Moved" in captured.out
        assert "[dry-run]" not in captured.out

    def test_move_run_log_with_dry_run_prints_dry_run_only(self, capsys):
        """run_log + dry_run：仅输出 dry-run 日志"""
        dst_file = self.dst_dir / "runlog_dry.txt"

        move(str(self.src_file), str(dst_file), run_log=True, dry_run=True)

        captured = capsys.readouterr()
        assert "[dry-run] Moved" in captured.out
        assert "\nMoved" not in captured.out

    def test_move_passes_copy_function_to_shutil_move(self, monkeypatch):
        """传入 copy_function 时应透传给 shutil.move"""
        calls = {}

        def fake_shutil_move(src, dst, copy_function=None):
            calls["src"] = src
            calls["dst"] = dst
            calls["copy_function"] = copy_function
            return dst

        def fake_copy_function(src, dst):
            return dst

        monkeypatch.setattr(operator_module.shutil, "move", fake_shutil_move)

        dst_file = self.dst_dir / "copied.txt"
        move(str(self.src_file), str(dst_file), copy_function=fake_copy_function)

        assert calls["src"] == str(self.src_file)
        assert calls["dst"] == str(dst_file)
        assert calls["copy_function"] is fake_copy_function


class TestCopy:

    @pytest.fixture(autouse=True)
    def setup_tmpdir(self, tmp_path):
        self.test_dir = tmp_path / "copy_root"
        self.test_dir.mkdir()

        self.src_dir = self.test_dir / "src"
        self.src_dir.mkdir()

        self.dst_dir = self.test_dir / "dst"
        self.dst_dir.mkdir()

        self.src_file = self.src_dir / "source.txt"
        self.src_file.write_text("source content")

        self.src_folder = self.src_dir / "source_folder"
        self.src_folder.mkdir()
        (self.src_folder / "inner.txt").write_text("inner content")

        yield

    def test_copy_to_file_path_success(self):
        """默认复制到目标文件路径：成功复制"""
        dst_file = self.dst_dir / "copied.txt"

        copy(str(self.src_file), str(dst_file))

        assert self.src_file.exists()
        assert dst_file.exists()
        assert dst_file.read_text() == "source content"

    def test_copy_relative_dst_bare_filename(self, monkeypatch):
        """Regression: 相对路径 dst 只有文件名时，父目录应视为 cwd 而非空串

        os.path.dirname('out.txt') 返回 ''，而 os.path.exists('') 恒为
        False，曾导致对 cwd 的复制误报 FileNotFoundError。"""
        monkeypatch.chdir(self.dst_dir)

        copy(str(self.src_file), "out.txt")

        assert (self.dst_dir / "out.txt").read_text() == "source content"

    def test_copy_relative_dst_make_dir(self, monkeypatch):
        """相对路径 dst + make_dir=True：在 cwd 下创建缺失的父目录"""
        monkeypatch.chdir(self.dst_dir)

        copy(str(self.src_file), os.path.join("new_sub", "deep", "out.txt"),
             make_dir=True)

        assert (self.dst_dir / "new_sub" / "deep" / "out.txt").read_text() \
            == "source content"

    def test_copy_to_existing_directory_success(self):
        """目标为已有目录：复制后文件进入该目录"""
        copy(str(self.src_file), str(self.dst_dir))

        copied_file = self.dst_dir / self.src_file.name
        assert self.src_file.exists()
        assert copied_file.exists()
        assert copied_file.read_text() == "source content"

    def test_copy_directory_success(self):
        """复制目录：复制整个目录树"""
        dst_folder = self.dst_dir / "copied_folder"

        copy(str(self.src_folder), str(dst_folder))

        assert self.src_folder.exists()
        assert dst_folder.exists()
        assert (dst_folder / "inner.txt").read_text() == "inner content"

    def test_copy_make_dir_true_creates_parent(self):
        """make_dir=True 时自动创建父目录并复制"""
        dst_file = self.test_dir / "new_parent" / "deep" / "copied.txt"

        copy(str(self.src_file), str(dst_file), make_dir=True)

        assert self.src_file.exists()
        assert dst_file.exists()
        assert dst_file.read_text() == "source content"

    def test_copy_make_dir_false_raises(self):
        """make_dir=False 且目标父目录不存在：抛出 FileNotFoundError"""
        dst_file = self.test_dir / "new_parent" / "deep" / "copied.txt"

        with pytest.raises(FileNotFoundError) as excinfo:
            copy(str(self.src_file), str(dst_file), make_dir=False)

        assert "does not exist" in str(excinfo.value)
        assert self.src_file.exists()

    def test_copy_exist_policy_overwrite(self):
        """exist_policy='overwrite'：先删除目标再复制"""
        dst_file = self.dst_dir / "target.txt"
        dst_file.write_text("old content")

        copy(str(self.src_file), str(dst_file), exist_policy='overwrite')

        assert self.src_file.exists()
        assert dst_file.exists()
        assert dst_file.read_text() == "source content"

    def test_copy_exist_policy_rename(self):
        """exist_policy='rename'：目标已存在时自动改名"""
        dst_file = self.dst_dir / "target.txt"
        dst_file.write_text("old content")

        renamed_0 = self.dst_dir / "target_0.txt"
        renamed_0.write_text("occupied")

        copy(str(self.src_file), str(dst_file), exist_policy='rename')

        renamed_1 = self.dst_dir / "target_1.txt"
        assert self.src_file.exists()
        assert dst_file.read_text() == "old content"
        assert renamed_0.read_text() == "occupied"
        assert renamed_1.exists()
        assert renamed_1.read_text() == "source content"

    def test_copy_exist_policy_invalid_raises(self):
        """非法 exist_policy：抛出 ValueError"""
        dst_file = self.dst_dir / "target.txt"
        dst_file.write_text("old content")

        with pytest.raises(ValueError) as excinfo:
            copy(str(self.src_file), str(dst_file), exist_policy='invalid')

        assert "exist_policy must be" in str(excinfo.value)
        assert self.src_file.exists()

    def test_copy_exist_policy_rename_custom_format_and_start(self):
        """exist_policy='rename' + 自定义格式/起始序号：Windows 风格命名"""
        dst_file = self.dst_dir / "target.txt"
        dst_file.write_text("old content")

        copy(str(self.src_file), str(dst_file), exist_policy='rename',
             rename_format='{stem} ({i}){suffix}', rename_start=1)

        renamed = self.dst_dir / "target (1).txt"
        assert self.src_file.exists()
        assert dst_file.read_text() == "old content"
        assert renamed.read_text() == "source content"

    def test_copy_rename_invalid_format_raises(self):
        """非法 rename_format：实际触发改名时抛 ValueError，不拷贝任何文件"""
        dst_file = self.dst_dir / "target.txt"
        dst_file.write_text("old content")

        with pytest.raises(ValueError, match="Invalid rename_format"):
            copy(str(self.src_file), str(dst_file), exist_policy='rename',
                 rename_format='{oops}')

        assert self.src_file.exists()
        assert dst_file.read_text() == "old content"
        assert not (self.dst_dir / "target_0.txt").exists()

    def test_copy_file_to_existing_file_default_overwrites(self):
        """Docstring (copy, table): file src + existing file dst +
        exist_policy='default' -> silently overwritten by copy2."""
        dst_file = self.dst_dir / "source.txt"
        dst_file.write_text("old")

        copy(str(self.src_file), str(dst_file))

        assert dst_file.read_text() == "source content"

    def test_copy_directory_to_existing_file_default_raises(self):
        """Docstring (copy, table/Raises): directory src + existing file
        dst + 'default' -> FileExistsError from copytree."""
        dst = self.dst_dir / "blocker.txt"
        dst.write_text("block")

        with pytest.raises(FileExistsError):
            copy(str(self.src_folder), str(dst))

    def test_copy_directory_to_existing_file_overwrite(self):
        """Docstring (copy, table): directory src + existing file dst +
        'overwrite' -> file removed first, then copytree."""
        dst = self.dst_dir / "blocker.txt"
        dst.write_text("block")

        copy(str(self.src_folder), str(dst), exist_policy='overwrite')

        assert dst.is_dir()
        assert (dst / "inner.txt").read_text() == "inner content"

    def test_copy_directory_to_existing_file_rename(self):
        """Docstring (copy, table): directory src + existing file dst +
        'rename' -> copytree to stem_0.ext."""
        dst = self.dst_dir / "blocker.txt"
        dst.write_text("block")

        copy(str(self.src_folder), str(dst), exist_policy='rename')

        assert dst.read_text() == "block"
        assert (self.dst_dir / "blocker_0.txt" / "inner.txt").is_file()

    def test_copy_directory_to_existing_dir_raises(self):
        """Docstring (copy, table): directory src + existing dir dst ->
        FileExistsError from copytree (exist_policy ignored for
        directory destinations)."""
        with pytest.raises(FileExistsError):
            copy(str(self.src_folder), str(self.dst_dir))

    def test_copy_dry_run_no_fs_change(self, capsys):
        """dry_run=True：不执行真实复制，但输出 dry-run 日志"""
        dst_file = self.dst_dir / "dry_copied.txt"

        copy(str(self.src_file), str(dst_file), dry_run=True)

        captured = capsys.readouterr()
        assert "[dry-run] Copied" in captured.out
        assert self.src_file.exists()
        assert not dst_file.exists()

    def test_copy_dry_run_overwrite_keeps_destination(self, capsys):
        """dry_run + overwrite：不删除原目标文件"""
        dst_file = self.dst_dir / "target.txt"
        dst_file.write_text("old content")

        copy(str(self.src_file),
             str(dst_file),
             dry_run=True,
             exist_policy='overwrite')

        captured = capsys.readouterr()
        assert "[dry-run] Removed existing file" in captured.out
        assert "[dry-run] Copied" in captured.out
        assert self.src_file.exists()
        assert dst_file.read_text() == "old content"

    def test_copy_run_log_prints_log(self, capsys):
        """run_log=True：输出执行日志（非 dry-run）"""
        dst_file = self.dst_dir / "runlog.txt"

        copy(str(self.src_file), str(dst_file), run_log=True)

        captured = capsys.readouterr()
        assert "Copied" in captured.out
        assert "[dry-run]" not in captured.out

    def test_copy_run_log_with_make_dir_prints_create(self, capsys):
        """run_log=True + make_dir=True：打印创建目录日志"""
        dst_file = self.test_dir / "new_parent" / "deep" / "runlog.txt"

        copy(str(self.src_file), str(dst_file), make_dir=True, run_log=True)

        captured = capsys.readouterr()
        assert "Create directory" in captured.out
        assert "Copied" in captured.out
        assert "[dry-run]" not in captured.out

    def test_copy_run_log_with_dry_run_prints_dry_run_only(self, capsys):
        """run_log + dry_run：仅输出 dry-run 日志"""
        dst_file = self.dst_dir / "runlog_dry.txt"

        copy(str(self.src_file), str(dst_file), run_log=True, dry_run=True)

        captured = capsys.readouterr()
        assert "[dry-run] Copied" in captured.out
        assert "\nCopied" not in captured.out

    def test_copy_file_uses_default_copy2(self, monkeypatch):
        """文件复制默认调用 shutil.copy2"""
        calls = {}

        def fake_copy2(src, dst):
            calls["src"] = src
            calls["dst"] = dst
            return dst

        monkeypatch.setattr(operator_module.shutil, "copy2", fake_copy2)

        dst_file = self.dst_dir / "copied.txt"
        copy(str(self.src_file), str(dst_file))

        assert calls["src"] == str(self.src_file)
        assert calls["dst"] == str(dst_file)

    def test_copy_file_passes_copy_function(self):
        """文件复制传入 copy_function 时应调用该函数"""
        calls = {}

        def fake_copy_function(src, dst):
            calls["src"] = src
            calls["dst"] = dst
            return dst

        dst_file = self.dst_dir / "custom.txt"
        copy(str(self.src_file), str(dst_file), copy_function=fake_copy_function)

        assert calls["src"] == str(self.src_file)
        assert calls["dst"] == str(dst_file)

    def test_copy_directory_passes_copy_function_to_copytree(self, monkeypatch):
        """目录复制传入 copy_function 时应透传给 shutil.copytree"""
        calls = {}

        def fake_copytree(src, dst, copy_function=None):
            calls["src"] = src
            calls["dst"] = dst
            calls["copy_function"] = copy_function
            return dst

        def fake_copy_function(src, dst):
            return dst

        monkeypatch.setattr(operator_module.shutil, "copytree", fake_copytree)

        dst_folder = self.dst_dir / "copied_folder"
        copy(str(self.src_folder),
             str(dst_folder),
             copy_function=fake_copy_function)

        assert calls["src"] == str(self.src_folder)
        assert calls["dst"] == str(dst_folder)
        assert calls["copy_function"] is fake_copy_function


def _make_link_or_skip(link_path: Path,
                       target: str,
                       target_is_directory: bool = False) -> None:
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
    """os.readlink with the Windows ``\\?\\`` long-path prefix stripped.

    Python's readlink on Windows can return targets with a ``\\?\\``
    prefix even when the link was created without one.
    """
    return os.readlink(str(link_path)).removeprefix("\\\\?\\")


class TestMapLinkTarget:
    """Tests for the pure string-math _map_link_target helper.

    No symlink privilege is required to run these.
    """

    def test_target_inside_src_is_remapped(self):
        """Docstring (_map_link_target): absolute target inside src_root
        is remapped to the same relative location under dst_root."""
        result = operator_module._map_link_target(
            r"C:\root\src_dir\sub\real.txt", r"C:\root\src_dir", r"D:\backup\copy")
        assert os.path.normpath(result) == \
            os.path.normpath(r"D:\backup\copy\sub\real.txt")

    def test_target_equal_to_src_root_maps_to_dst_root(self):
        """Docstring (_map_link_target): target == src_root itself maps
        to dst_root (edge case, must not crash)."""
        result = operator_module._map_link_target(
            r"C:\root\src_dir", r"C:\root\src_dir", r"D:\dst")
        assert os.path.normpath(result) == os.path.normpath(r"D:\dst")

    def test_target_outside_src_unchanged(self):
        """Docstring (_map_link_target): absolute target outside src_root
        is returned verbatim."""
        target = r"C:\root\external\file.txt"
        result = operator_module._map_link_target(
            target, r"C:\root\src_dir", r"D:\dst")
        assert result == target

    def test_relative_target_unchanged(self):
        """Docstring (_map_link_target): relative targets are returned
        verbatim (they still resolve correctly after a tree move)."""
        result = operator_module._map_link_target(
            "real.txt", r"C:\root\src_dir", r"D:\dst")
        assert result == "real.txt"

    def test_cross_drive_target_unchanged(self):
        """Docstring (_map_link_target): cross-drive targets are returned
        verbatim (commonpath raises ValueError internally)."""
        target = r"D:\other\file.txt"
        result = operator_module._map_link_target(
            target, r"C:\root\src_dir", r"D:\dst")
        assert result == target

    def test_windows_long_path_prefix_preserved(self):
        """Docstring (_map_link_target): the Windows \\\\?\\ long-path
        prefix survives the mapping."""
        target = r"\\?\C:\root\src_dir\sub\real.txt"
        result = operator_module._map_link_target(
            target, r"C:\root\src_dir", r"D:\dst")
        assert result.startswith("\\\\?\\")
        assert os.path.normpath(result.removeprefix("\\\\?\\")) == \
            os.path.normpath(r"D:\dst\sub\real.txt")

    def test_nonexistent_src_root_still_works(self):
        """Docstring (_map_link_target): pure string math — works after
        a same-drive move when src_root no longer exists."""
        result = operator_module._map_link_target(
            r"C:\gone\src_dir\sub\real.txt", r"C:\gone\src_dir", r"D:\dst")
        assert os.path.normpath(result) == os.path.normpath(r"D:\dst\sub\real.txt")


class TestCopySymlinks:
    """Tests for copy's preserve_symlinks flag."""

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
        (self.src_dir / "sub" / "nested.txt").write_text("nested")

        # absolute target inside src -> retargeted
        self.link_file = self.src_dir / "link_file"
        _make_link_or_skip(self.link_file, str(self.src_dir / "real.txt"))
        # absolute dir target inside src -> retargeted
        self.link_dir = self.src_dir / "link_dir"
        _make_link_or_skip(self.link_dir, str(self.src_dir / "sub"),
                           target_is_directory=True)
        # absolute target outside src -> verbatim
        self.link_ext = self.src_dir / "link_ext"
        _make_link_or_skip(self.link_ext, str(self.external / "outside.txt"))
        # relative target -> verbatim
        self.link_rel = self.src_dir / "link_rel"
        _make_link_or_skip(self.link_rel, "real.txt")

        self.dst = self.root / "dst"

        yield

    def test_default_follows_symlinks(self, capsys):
        """Default off: symlinks are dereferenced and copied as content."""
        copy(str(self.src_dir), str(self.dst))

        assert not (self.dst / "link_file").is_symlink()
        assert (self.dst / "link_file").is_file()
        assert not (self.dst / "link_dir").is_symlink()
        assert (self.dst / "link_dir").is_dir()
        assert (self.dst / "link_dir" / "nested.txt").read_text() == "nested"

        captured = capsys.readouterr()
        assert "[RETARGET]" not in captured.out

    def test_preserve_and_retarget_keeps_links_and_retargets(self):
        """Docstring (copy, flags table): preserve + retarget on a
        directory tree -> links kept as links; absolute in-tree targets
        rewritten to the copy; outside/relative links verbatim."""
        copy(str(self.src_dir), str(self.dst), preserve_symlinks=True,
             retarget_symlinks=True)

        dst_link_file = self.dst / "link_file"
        dst_link_dir = self.dst / "link_dir"
        assert dst_link_file.is_symlink()
        assert dst_link_dir.is_symlink()

        # in-tree absolute targets are retargeted to the copy
        assert os.path.normpath(_readlink_clean(dst_link_file)) == \
            os.path.normpath(str(self.dst / "real.txt"))
        # the dir link resolves inside the copy (not dangling)
        assert dst_link_dir.resolve() == (self.dst / "sub").resolve()

        # outside / relative targets still resolve as before (not retargeted)
        assert (self.dst / "link_ext").resolve() == \
            (self.external / "outside.txt").resolve()
        assert (self.dst / "link_rel").resolve() == \
            (self.dst / "real.txt").resolve()

    @pytest.mark.skipif(os.name != "nt", reason="Windows \\\\?\\ prefix semantics")
    def test_preserve_keeps_windows_long_path_prefix(self):
        """Docstring (copy, preserve_symlinks param): retargeting keeps
        the Windows \\\\?\\ long-path prefix on remapped targets."""
        long_target = "\\\\?\\" + str(self.src_dir / "real.txt")
        _make_link_or_skip(self.src_dir / "link_long", long_target)

        copy(str(self.src_dir), str(self.dst), preserve_symlinks=True,
             retarget_symlinks=True)

        new_target = os.readlink(str(self.dst / "link_long"))
        assert new_target.startswith("\\\\?\\")
        assert os.path.normpath(new_target.removeprefix("\\\\?\\")) == \
            os.path.normpath(str(self.dst / "real.txt"))

    def test_single_symlink_file_copy_flag_on_recreates_link(self):
        """Docstring (copy, flags table): symlink src + preserve on ->
        recreated as a link with the original target, never retargeted."""
        link = self.root / "single_link"
        _make_link_or_skip(link, str(self.src_dir / "real.txt"))
        dst_link = self.root / "single_link_copied"

        copy(str(link), str(dst_link), preserve_symlinks=True)

        assert dst_link.is_symlink()
        assert os.path.normpath(_readlink_clean(dst_link)) == \
            os.path.normpath(str(self.src_dir / "real.txt"))

    def test_single_symlink_file_copy_flag_off_copies_content(self):
        """Docstring (copy, flags table): symlink src + flags off ->
        followed; dst is a real file with the target's content (copy2
        follows symlinks)."""
        link = self.root / "single_link"
        _make_link_or_skip(link, str(self.src_dir / "real.txt"))
        dst_link = self.root / "single_link_copied"

        copy(str(link), str(dst_link))

        assert not dst_link.is_symlink()
        assert dst_link.read_text() == "real"

    def test_single_symlink_dir_copy_flag_on_recreates_link(self):
        """Docstring (copy, flags table): directory-link src + preserve
        on -> recreated as a link (not a real directory copy)."""
        link = self.root / "single_dlink"
        _make_link_or_skip(link, str(self.src_dir / "sub"),
                           target_is_directory=True)
        dst_link = self.root / "single_dlink_copied"

        copy(str(link), str(dst_link), preserve_symlinks=True)

        assert dst_link.is_symlink()
        assert dst_link.resolve() == (self.src_dir / "sub").resolve()

    def test_single_symlink_copy_into_existing_dir(self):
        """Docstring (copy, dst param): symlink src + existing dir dst ->
        the link is recreated inside it as dst/<basename(src)>."""
        link = self.root / "single_link"
        _make_link_or_skip(link, str(self.src_dir / "real.txt"))
        self.dst.mkdir()

        copy(str(link), str(self.dst), preserve_symlinks=True)

        assert (self.dst / "single_link").is_symlink()

    def test_symlink_to_existing_file_default_preserve_on_raises(self):
        """Docstring (copy, table/Raises): symlink src + existing file
        dst + 'default' + preserve on -> FileExistsError from os.symlink
        (plain copy2 would silently overwrite)."""
        link = self.root / "single_link2"
        _make_link_or_skip(link, str(self.src_dir / "real.txt"))
        dst = self.root / "blocker.txt"
        dst.write_text("block")

        with pytest.raises(FileExistsError):
            copy(str(link), str(dst), preserve_symlinks=True)

        assert dst.read_text() == "block"
        assert link.is_symlink()

    def test_symlink_to_existing_file_default_preserve_off_overwrites(self):
        """Docstring (copy, table): symlink src + existing file dst +
        'default' + preserve off -> copy2 follows the link and
        overwrites the file with the target's content."""
        link = self.root / "single_link2"
        _make_link_or_skip(link, str(self.src_dir / "real.txt"))
        dst = self.root / "blocker.txt"
        dst.write_text("block")

        copy(str(link), str(dst))

        assert not dst.is_symlink()
        assert dst.read_text() == "real"

    def test_symlink_to_existing_file_overwrite_preserve_on(self):
        """Docstring (copy, table): symlink src + existing file dst +
        'overwrite' + preserve on -> file removed first, link recreated."""
        link = self.root / "single_link2"
        _make_link_or_skip(link, str(self.src_dir / "real.txt"))
        dst = self.root / "blocker.txt"
        dst.write_text("block")

        copy(str(link), str(dst), exist_policy='overwrite',
             preserve_symlinks=True)

        assert dst.is_symlink()
        assert dst.resolve() == (self.src_dir / "real.txt").resolve()

    def test_default_copytree_raises_on_dangling_link(self):
        """Docstring (copy, flags table): directory tree containing a
        dangling link + flags off -> copytree follows the link and
        raises shutil.Error."""
        _make_link_or_skip(self.src_dir / "link_dangling",
                           str(self.root / "gone.txt"))

        with pytest.raises(shutil.Error):
            copy(str(self.src_dir), str(self.dst))

    def test_dry_run_previews_retargets(self, capsys):
        """Docstring (copy, Notes): dry_run prints
        '[dry-run] [RETARGET] ...' for every link that would be
        rewritten, and creates nothing."""
        copy(str(self.src_dir), str(self.dst), preserve_symlinks=True,
             retarget_symlinks=True, dry_run=True)

        assert not self.dst.exists()
        captured = capsys.readouterr()
        assert "[dry-run] [RETARGET]" in captured.out

    def test_run_log_reports_retargets(self, capsys):
        """Docstring (copy, run_log param): a real run prints one
        '[RETARGET]' line per rewritten link when run_log=True."""
        copy(str(self.src_dir), str(self.dst), preserve_symlinks=True,
             retarget_symlinks=True, run_log=True)

        captured = capsys.readouterr()
        assert "[RETARGET]" in captured.out
        assert "[dry-run]" not in captured.out

    def test_preserve_without_retarget_keeps_original_targets(self):
        """Docstring (copy, flags table): preserve on + retarget off ->
        inner links kept as links with their original targets
        unchanged (still pointing into the source)."""
        copy(str(self.src_dir), str(self.dst), preserve_symlinks=True)

        dst_link_file = self.dst / "link_file"
        assert dst_link_file.is_symlink()
        # original absolute target kept: still points into the source
        assert os.path.normpath(_readlink_clean(dst_link_file)) == \
            os.path.normpath(str(self.src_dir / "real.txt"))
        assert dst_link_file.resolve() == \
            (self.src_dir / "real.txt").resolve()

    def test_retarget_without_preserve_warns_and_does_nothing(self, capsys):
        """Docstring (copy, retarget_symlinks param / Notes):
        retarget_symlinks=True without preserve_symlinks=True prints a
        warning, follows the links and retargets nothing."""
        copy(str(self.src_dir), str(self.dst), retarget_symlinks=True)

        # links followed (real files in dst), nothing retargeted
        assert not (self.dst / "link_file").is_symlink()
        assert (self.dst / "link_file").is_file()

        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "retarget_symlinks" in captured.out
        assert "[RETARGET]" not in captured.out

    def test_preserve_passes_symlinks_true_to_copytree(self, monkeypatch):
        """Docstring (copy, preserve_symlinks param): a directory copy
        with preserve on passes symlinks=True to copytree (links are
        recreated as links, not followed)."""
        calls = {}

        def fake_copytree(src, dst, copy_function=None, symlinks=False):
            calls["symlinks"] = symlinks
            return dst

        monkeypatch.setattr(operator_module.shutil, "copytree", fake_copytree)
        copy(str(self.src_dir), str(self.dst), preserve_symlinks=True)

        assert calls["symlinks"] is True

    def test_default_passes_no_symlinks_kwarg_to_copytree(self, monkeypatch):
        """Docstring (copy): flags off -> copytree is called with its
        default symlinks=False (current behavior unchanged)."""
        calls = {}

        def fake_copytree(src, dst, copy_function=None, symlinks=False):
            calls["symlinks"] = symlinks
            return dst

        monkeypatch.setattr(operator_module.shutil, "copytree", fake_copytree)
        copy(str(self.src_dir), str(self.dst))

        assert calls["symlinks"] is False


class TestMoveSymlinks:
    """Tests for move's preserve_symlinks flag."""

    @pytest.fixture(autouse=True)
    def setup_tree(self, tmp_path: Path) -> None:
        self.root = tmp_path / "move_root"
        self.root.mkdir()

        self.external = self.root / "external"
        self.external.mkdir()
        (self.external / "outside.txt").write_text("outside")

        self.src_dir = self.root / "src_dir"
        (self.src_dir / "sub").mkdir(parents=True)
        (self.src_dir / "real.txt").write_text("real")
        (self.src_dir / "sub" / "nested.txt").write_text("nested")

        self.link_file = self.src_dir / "link_file"
        _make_link_or_skip(self.link_file, str(self.src_dir / "real.txt"))
        self.link_dir = self.src_dir / "link_dir"
        _make_link_or_skip(self.link_dir, str(self.src_dir / "sub"),
                           target_is_directory=True)
        self.link_rel = self.src_dir / "link_rel"
        _make_link_or_skip(self.link_rel, "real.txt")

        yield

    def test_preserve_retargets_in_tree_links_after_move(self):
        """Core feature: a same-drive move leaves in-tree absolute links
        dangling; the flag rewrites them to the moved tree."""
        dst_dir = self.root / "moved"

        move(str(self.src_dir), str(dst_dir), retarget_symlinks=True)

        moved_link = dst_dir / "link_file"
        assert moved_link.is_symlink()
        assert os.path.normpath(_readlink_clean(moved_link)) == \
            os.path.normpath(str(dst_dir / "real.txt"))

        moved_dlink = dst_dir / "link_dir"
        assert moved_dlink.resolve() == (dst_dir / "sub").resolve()

        # relative link still resolves inside the moved tree
        assert (dst_dir / "link_rel").resolve() == \
            (dst_dir / "real.txt").resolve()

    def test_default_leaves_in_tree_links_dangling(self):
        """Without the flag, the rename keeps the old absolute target,
        which no longer exists."""
        dst_dir = self.root / "moved"

        move(str(self.src_dir), str(dst_dir))

        assert (dst_dir / "link_file").is_symlink()
        assert not (dst_dir / "link_file").exists()

    def test_move_into_existing_dir_retargets_to_landing_root(self):
        """Docstring (move, table): directory src + existing dir dst ->
        tree lands at dst/<basename(src)> and the retarget pass uses
        that landing root."""
        dst_container = self.root / "dst_container"
        dst_container.mkdir()

        move(str(self.src_dir), str(dst_container), retarget_symlinks=True)

        land_root = dst_container / "src_dir"
        assert land_root.is_dir()
        assert os.path.normpath(_readlink_clean(land_root / "link_file")) == \
            os.path.normpath(str(land_root / "real.txt"))

    def test_single_symlink_move_keeps_link(self):
        """Docstring (move, table): a single symlink src is moved as a
        link with its original target and never retargeted, with the
        flag off or on."""
        for flag in (False, True):
            link = self.root / f"single_link_{flag}"
            _make_link_or_skip(link, str(self.src_dir / "real.txt"))
            dst_link = self.root / f"single_link_moved_{flag}"

            move(str(link), str(dst_link), retarget_symlinks=flag)

            assert dst_link.is_symlink()
            assert os.path.normpath(_readlink_clean(dst_link)) == \
                os.path.normpath(str(self.src_dir / "real.txt"))

    def test_symlink_to_existing_file_default_raises(self):
        """Docstring (move, table/Raises): symlink src + existing file
        dst + 'default' -> FileExistsError (os.rename cannot replace a
        file with a link); the link is left in place."""
        link = self.root / "link4"
        _make_link_or_skip(link, str(self.src_dir / "real.txt"))
        dst = self.root / "blocker.txt"
        dst.write_text("block")

        with pytest.raises(FileExistsError):
            move(str(link), str(dst))

        assert link.is_symlink()

    def test_symlink_to_existing_file_overwrite(self):
        """Docstring (move, table): symlink src + existing file dst +
        'overwrite' -> existing file removed first, then link moved."""
        link = self.root / "link4"
        _make_link_or_skip(link, str(self.src_dir / "real.txt"))
        dst = self.root / "blocker.txt"
        dst.write_text("block")

        move(str(link), str(dst), exist_policy='overwrite')

        assert dst.is_symlink()
        assert not link.exists()

    def test_symlink_to_existing_file_rename(self):
        """Docstring (move, table): symlink src + existing file dst +
        'rename' -> link moved to stem_0.ext."""
        link = self.root / "link4"
        _make_link_or_skip(link, str(self.src_dir / "real.txt"))
        dst = self.root / "blocker.txt"
        dst.write_text("block")

        move(str(link), str(dst), exist_policy='rename')

        assert dst.read_text() == "block"
        assert (self.root / "blocker_0.txt").is_symlink()

    def test_symlink_to_existing_dir_lands_inside(self):
        """Docstring (move, table): symlink src + existing dir dst ->
        moved into it as dst/<basename(src)>, still a link."""
        link = self.root / "link4"
        _make_link_or_skip(link, str(self.src_dir / "real.txt"))
        container = self.root / "container"
        container.mkdir()

        move(str(link), str(container))

        assert (container / "link4").is_symlink()

    def test_dry_run_previews_retargets(self, capsys):
        """Docstring (move, Notes): dry_run prints
        '[dry-run] [RETARGET] ...' for every link that would be
        rewritten, and moves nothing."""
        dst_dir = self.root / "moved"

        move(str(self.src_dir), str(dst_dir), retarget_symlinks=True,
             dry_run=True)

        assert self.src_dir.exists()
        assert not dst_dir.exists()
        captured = capsys.readouterr()
        assert "[dry-run] [RETARGET]" in captured.out


class TestSymlinkPrivilegePrecheck:
    """Privilege pre-check plumbing tests.

    No real symlinks are created, so these run in any environment;
    the walk helpers are monkeypatched to pretend links exist.
    """

    @pytest.fixture(autouse=True)
    def setup_tree(self, tmp_path: Path) -> None:
        self.root = tmp_path / "plain_root"
        self.src_dir = self.root / "src_dir"
        (self.src_dir / "sub").mkdir(parents=True)
        (self.src_dir / "real.txt").write_text("real")
        self.dst = self.root / "dst"

    @staticmethod
    def _raise_perm():
        raise PermissionError("no privilege")

    def test_copy_precheck_raises_before_mutation(self, monkeypatch):
        """Docstring (copy, Raises): preserve on + tree containing links
        + missing symlink privilege -> PermissionError before anything
        is copied (dst is not created)."""
        monkeypatch.setattr(operator_module, "_iter_symlinks",
                            lambda root: iter([os.path.join(root, "fake")]))
        monkeypatch.setattr(operator_module, "_check_symlink_privilege",
                            self._raise_perm)

        with pytest.raises(PermissionError, match="no privilege"):
            copy(str(self.src_dir), str(self.dst), preserve_symlinks=True)

        assert not self.dst.exists()  # nothing was written

    def test_copy_precheck_skipped_without_links(self, monkeypatch):
        """Docstring (copy, preserve_symlinks param): no links in the
        tree -> the privilege probe is skipped and the copy succeeds
        even without symlink rights."""
        def spy():
            raise AssertionError("privilege probe must not be called")
        monkeypatch.setattr(operator_module, "_check_symlink_privilege", spy)

        copy(str(self.src_dir), str(self.dst), preserve_symlinks=True)

        # no links in the tree -> no probe -> copy succeeds anywhere
        assert self.dst.is_dir()

    def test_copy_precheck_dry_run_also_raises(self, monkeypatch):
        """Docstring (copy, dry_run param): the privilege pre-check runs
        in dry_run mode too, so previews double as feasibility checks."""
        monkeypatch.setattr(operator_module, "_iter_symlinks",
                            lambda root: iter([os.path.join(root, "fake")]))
        monkeypatch.setattr(operator_module, "_check_symlink_privilege",
                            self._raise_perm)

        with pytest.raises(PermissionError, match="no privilege"):
            copy(str(self.src_dir), str(self.dst), preserve_symlinks=True,
                 dry_run=True)

        assert not self.dst.exists()

    def test_move_precheck_raises_before_mutation(self, monkeypatch):
        """Docstring (move, Raises): retarget on + at least one link
        would be rewritten + missing privilege -> PermissionError before
        anything is moved (src stays in place)."""
        fake = [(str(self.root / "fake"), "old", "new")]
        monkeypatch.setattr(operator_module, "_iter_retargets",
                            lambda root, s, d: iter(fake))
        monkeypatch.setattr(operator_module, "_check_symlink_privilege",
                            self._raise_perm)

        with pytest.raises(PermissionError, match="no privilege"):
            move(str(self.src_dir), str(self.dst), retarget_symlinks=True)

        assert self.src_dir.exists()  # nothing was moved
        assert not self.dst.exists()

    def test_move_precheck_dry_run_also_raises(self, monkeypatch):
        """Docstring (move, dry_run param): the privilege pre-check runs
        in dry_run mode too (infeasible move fails in the preview)."""
        fake = [(str(self.root / "fake"), "old", "new")]
        monkeypatch.setattr(operator_module, "_iter_retargets",
                            lambda root, s, d: iter(fake))
        monkeypatch.setattr(operator_module, "_check_symlink_privilege",
                            self._raise_perm)

        with pytest.raises(PermissionError, match="no privilege"):
            move(str(self.src_dir), str(self.dst), retarget_symlinks=True,
                 dry_run=True)

        assert self.src_dir.exists()
        assert not self.dst.exists()

    def test_move_precheck_skipped_without_rewritable_links(self,
                                                            monkeypatch):
        """Docstring (move, retarget_symlinks param): retarget on but no
        link target would actually change -> no probe, the plain rename
        succeeds without symlink rights."""
        def spy():
            raise AssertionError("privilege probe must not be called")
        monkeypatch.setattr(operator_module, "_check_symlink_privilege", spy)

        move(str(self.src_dir), str(self.dst), retarget_symlinks=True)

        # no rewritable links -> no probe -> plain rename succeeds
        assert not self.src_dir.exists()
        assert self.dst.is_dir()


class TestMergeFolders:
    """Tests for merge_folders function."""

    @pytest.fixture(autouse=True)
    def setup_tree(self, tmp_path: Path) -> None:
        """Build the standard source/target tree.

        Expected merge result: 2 copied, 1 skipped, 2 renamed.
        """
        self.src = tmp_path / "src"
        self.dst = tmp_path / "dst"
        self.src.mkdir()
        self.dst.mkdir()

        # new_file.txt: only in src -> copied
        (self.src / "new_file.txt").write_text("brand new")
        # same.txt: identical on both sides -> skipped
        (self.src / "same.txt").write_text("same content")
        (self.dst / "same.txt").write_text("same content")
        # diff.txt: different content -> renamed
        (self.src / "diff.txt").write_text("source version")
        (self.dst / "diff.txt").write_text("target version")
        # as_dir.txt: dst side is a directory -> renamed
        (self.src / "as_dir.txt").write_text("source as dir")
        (self.dst / "as_dir.txt").mkdir()
        # nested/deep.txt: parent directory must be created in dst
        (self.src / "nested").mkdir()
        (self.src / "nested" / "deep.txt").write_text("deep")
        # empty_dir: must not be created in dst
        (self.src / "empty_dir").mkdir()
        # extra.txt: only in dst -> untouched
        (self.dst / "extra.txt").write_text("target only")

    def test_copy_new_file(self):
        """A file missing in dst is copied."""
        merge_folders(self.src, self.dst)

        assert (self.dst / "new_file.txt").read_text() == "brand new"

    def test_copy_creates_parent_directories(self):
        """Missing parent directories in dst are created automatically."""
        merge_folders(self.src, self.dst)

        assert (self.dst / "nested" / "deep.txt").read_text() == "deep"

    def test_skip_identical_file(self):
        """A file with identical SHA-256 on both sides is skipped."""
        merge_folders(self.src, self.dst)

        assert (self.dst / "same.txt").read_text() == "same content"
        assert not (self.dst / "same_0.txt").exists()

    def test_rename_different_content(self):
        """A conflicting file is kept in dst; the source is copied under a new name."""
        merge_folders(self.src, self.dst)

        assert (self.dst / "diff.txt").read_text() == "target version"
        assert (self.dst / "diff_0.txt").read_text() == "source version"

    def test_rename_when_destination_is_directory(self):
        """A source file is renamed when the same dst path is a directory."""
        merge_folders(self.src, self.dst)

        assert (self.dst / "as_dir.txt").is_dir()
        assert (self.dst / "as_dir_0.txt").read_text() == "source as dir"

    def test_rename_skips_occupied_suffix(self):
        """Occupied rename suffixes are skipped until a free one is found."""
        (self.dst / "diff_0.txt").write_text("occupied")
        (self.dst / "diff_1.txt").write_text("occupied")

        merge_folders(self.src, self.dst)

        assert (self.dst / "diff_0.txt").read_text() == "occupied"
        assert (self.dst / "diff_1.txt").read_text() == "occupied"
        assert (self.dst / "diff_2.txt").read_text() == "source version"

    def test_nested_conflict_renamed_in_subdir(self, tmp_path):
        """Conflicts inside subdirectories are renamed in place."""
        src = tmp_path / "src2"
        dst = tmp_path / "dst2"
        (src / "nested").mkdir(parents=True)
        (dst / "nested").mkdir(parents=True)
        (src / "nested" / "x.txt").write_text("source")
        (dst / "nested" / "x.txt").write_text("target")

        merge_folders(src, dst)

        assert (dst / "nested" / "x.txt").read_text() == "target"
        assert (dst / "nested" / "x_0.txt").read_text() == "source"

    def test_rename_format_custom(self):
        """Conflicting files are renamed according to a custom format."""
        merge_folders(self.src, self.dst,
                      rename_format='{stem} ({i}){suffix}')

        assert (self.dst / "diff (0).txt").read_text() == "source version"
        assert (self.dst / "as_dir (0).txt").read_text() == "source as dir"

    def test_rename_start_one(self):
        """Candidate numbering starts at rename_start."""
        merge_folders(self.src, self.dst, rename_start=1)

        assert (self.dst / "diff_1.txt").read_text() == "source version"
        assert (self.dst / "as_dir_1.txt").read_text() == "source as dir"

    def test_dry_run_preview_shows_custom_rename_name(self, capsys):
        """Dry-run preview lines show the custom rename name."""
        merge_folders(self.src, self.dst, dry_run=True,
                      rename_format='{stem} ({i}){suffix}')

        out = capsys.readouterr().out
        assert "[dry-run] [RENAME] diff.txt -> diff (0).txt" in out

    def test_invalid_rename_format_raises_before_any_copy(self):
        """An invalid format raises before any file is copied."""
        with pytest.raises(ValueError, match="Invalid rename_format"):
            merge_folders(self.src, self.dst, rename_format='{stem}')

        assert not (self.dst / "new_file.txt").exists()

    def test_empty_source_dir_not_created(self):
        """Empty directories in src are not created in dst."""
        merge_folders(self.src, self.dst)

        assert not (self.dst / "empty_dir").exists()

    def test_extra_dst_files_untouched(self):
        """Files that exist only in dst are left untouched."""
        merge_folders(self.src, self.dst)

        assert (self.dst / "extra.txt").read_text() == "target only"

    def test_returns_statistics_dict(self):
        """The returned statistics match the expected merge outcome."""
        result = merge_folders(self.src, self.dst)

        assert result == {"copied": 2, "skipped": 1, "renamed": 2}

    def test_dry_run_makes_no_changes(self):
        """dry_run=True previews without touching the filesystem."""
        merge_folders(self.src, self.dst, dry_run=True)

        assert not (self.dst / "new_file.txt").exists()
        assert not (self.dst / "diff_0.txt").exists()
        assert not (self.dst / "as_dir_0.txt").exists()
        assert not (self.dst / "nested").exists()

    def test_dry_run_prints_preview(self, capsys):
        """dry_run=True prints preview lines for every action."""
        merge_folders(self.src, self.dst, dry_run=True)

        captured = capsys.readouterr()
        assert "[dry-run] [COPY] new_file.txt" in captured.out
        assert "[dry-run] [COPY] nested/deep.txt" in captured.out
        assert "[dry-run] [SKIP] same.txt (same SHA-256)" in captured.out
        assert ("[dry-run] [RENAME] diff.txt -> diff_0.txt "
                "(different SHA-256)") in captured.out
        assert ("[dry-run] [RENAME] as_dir.txt -> as_dir_0.txt "
                "(destination is not a file)") in captured.out

    def test_dry_run_still_hashes_identical_files(self):
        """dry_run still hashes, so skipped statistics are accurate."""
        result = merge_folders(self.src, self.dst, dry_run=True)

        assert result["skipped"] == 1

    def test_run_log_prints_actions(self, capsys):
        """run_log=True prints a log line for every action."""
        merge_folders(self.src, self.dst, run_log=True)

        captured = capsys.readouterr()
        assert "[COPY] new_file.txt" in captured.out
        assert "[SKIP] same.txt (same SHA-256)" in captured.out
        assert "[RENAME] diff.txt -> diff_0.txt (different SHA-256)" in captured.out
        assert "[dry-run]" not in captured.out

    def test_default_quiet(self, capsys):
        """Default invocation prints nothing."""
        merge_folders(self.src, self.dst)

        assert capsys.readouterr().out == ""

    def test_run_log_and_dry_run_prints_dry_run_only(self, capsys):
        """With both flags set, only dry-run preview lines are printed."""
        merge_folders(self.src, self.dst, dry_run=True, run_log=True)

        captured = capsys.readouterr()
        assert "[dry-run]" in captured.out
        assert "\n[COPY]" not in captured.out

    def test_src_not_found_raises(self):
        """Missing src raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="not found"):
            merge_folders(self.src / "missing", self.dst)

    def test_dst_not_found_raises(self):
        """Missing dst raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="not found"):
            merge_folders(self.src, self.dst / "missing")

    def test_src_not_a_directory_raises(self, tmp_path):
        """A non-directory src raises ValueError."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        with pytest.raises(ValueError, match="Not a directory"):
            merge_folders(file_path, self.dst)

    def test_dst_not_a_directory_raises(self, tmp_path):
        """A non-directory dst raises ValueError."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        with pytest.raises(ValueError, match="Not a directory"):
            merge_folders(self.src, file_path)

    def test_same_src_and_dst_raises(self):
        """Merging a folder into itself raises ValueError."""
        with pytest.raises(ValueError, match="must be different"):
            merge_folders(self.src, self.src)

    def test_dst_inside_src_raises(self):
        """A dst nested inside src raises ValueError."""
        nested_dst = self.src / "dst"
        nested_dst.mkdir()

        with pytest.raises(ValueError, match="inside the source"):
            merge_folders(self.src, nested_dst)

    def test_string_paths_accepted(self):
        """String paths are accepted."""
        result = merge_folders(str(self.src), str(self.dst))

        assert result == {"copied": 2, "skipped": 1, "renamed": 2}

    def test_copy_called_with_make_dir(self, monkeypatch):
        """operator.copy is called with make_dir=True and string paths."""
        calls = []

        def fake_copy(src, dst, **kwargs):
            calls.append((src, dst, kwargs))

        monkeypatch.setattr(operator_module, "copy", fake_copy)

        merge_folders(self.src, self.dst)

        assert len(calls) == 4
        for src_arg, dst_arg, kwargs in calls:
            assert isinstance(src_arg, str)
            assert isinstance(dst_arg, str)
            assert kwargs == {"make_dir": True}

    def test_empty_src_folder_returns_zeros(self, tmp_path):
        """An empty src merges without error and returns zero statistics."""
        src = tmp_path / "src_empty"
        dst = tmp_path / "dst_empty"
        src.mkdir()
        dst.mkdir()

        result = merge_folders(src, dst)

        assert result == {"copied": 0, "skipped": 0, "renamed": 0}

    def test_end_to_end_preview_then_merge(self, capsys):
        """Full flow: dry-run preview, then execute, then verify the final state."""
        # preview: nothing written, accurate statistics
        stats = merge_folders(self.src, self.dst, dry_run=True)
        assert stats == {"copied": 2, "skipped": 1, "renamed": 2}
        assert not (self.dst / "new_file.txt").exists()
        assert "[dry-run]" in capsys.readouterr().out

        # execute and verify the final state
        stats = merge_folders(self.src, self.dst, run_log=True)
        assert stats == {"copied": 2, "skipped": 1, "renamed": 2}
        assert (self.dst / "new_file.txt").read_text() == "brand new"
        assert (self.dst / "nested" / "deep.txt").read_text() == "deep"
        assert (self.dst / "diff.txt").read_text() == "target version"  # untouched
        assert (self.dst / "diff_0.txt").read_text() == "source version"
        assert (self.dst / "as_dir.txt").is_dir()
        assert (self.dst / "as_dir_0.txt").read_text() == "source as dir"
        assert (self.dst / "extra.txt").read_text() == "target only"


class TestGetUniqueNewDst:
    """Tests for the get_unique_new_dst rename-template function."""

    @pytest.fixture(autouse=True)
    def setup_dir(self, tmp_path: Path) -> None:
        """Create a scratch directory for candidate names."""
        self.dir = tmp_path / "ren"
        self.dir.mkdir()

    def test_default_format_returns_first_free(self):
        """Default template yields stem_0.ext with forward slashes."""
        result = get_unique_new_dst(str(self.dir / "diff.txt"), 100)

        assert result == (self.dir / "diff_0.txt").as_posix()

    def test_default_format_skips_occupied_candidates(self):
        """Occupied candidates are skipped until a free one is found."""
        (self.dir / "diff_0.txt").write_text("occupied")
        (self.dir / "diff_1.txt").write_text("occupied")

        result = get_unique_new_dst(str(self.dir / "diff.txt"), 100)

        assert result == (self.dir / "diff_2.txt").as_posix()

    def test_custom_format_parentheses(self):
        """A custom template controls the candidate layout."""
        result = get_unique_new_dst(str(self.dir / "diff.txt"), 100,
                                    rename_format='{stem} ({i}){suffix}')

        assert result == (self.dir / "diff (0).txt").as_posix()

    def test_rename_start_one(self):
        """Numbering starts at rename_start."""
        result = get_unique_new_dst(str(self.dir / "diff.txt"), 100,
                                    rename_start=1)

        assert result == (self.dir / "diff_1.txt").as_posix()

    def test_rename_start_with_occupied_candidates(self):
        """Occupied candidates above rename_start are skipped."""
        (self.dir / "diff_1.txt").write_text("occupied")

        result = get_unique_new_dst(str(self.dir / "diff.txt"), 100,
                                    rename_start=1)

        assert result == (self.dir / "diff_2.txt").as_posix()

    def test_index_format_spec_zero_padding(self):
        """Format specs on {i} such as zero padding are supported."""
        result = get_unique_new_dst(str(self.dir / "diff.txt"), 100,
                                    rename_format='{stem}_{i:03d}{suffix}')

        assert result == (self.dir / "diff_000.txt").as_posix()

    def test_file_without_suffix(self):
        """A name without suffix gets no stray dot."""
        result = get_unique_new_dst(str(self.dir / "README"), 100)

        assert result == (self.dir / "README_0").as_posix()

    def test_multi_dot_name_moves_only_last_suffix(self):
        """Only the final suffix is treated as {suffix}."""
        result = get_unique_new_dst(str(self.dir / "a.tar.gz"), 100)

        assert result == (self.dir / "a.tar_0.gz").as_posix()

    def test_full_path_keeps_directories(self):
        """{stem} keeps the directory part of the passed path."""
        nested = self.dir / "nested"
        nested.mkdir()

        result = get_unique_new_dst(str(nested / "diff.txt"), 100)

        assert result == (nested / "diff_0.txt").as_posix()

    def test_template_without_index_placeholder_raises(self):
        """A constant template raises ValueError instead of looping."""
        with pytest.raises(ValueError, match="varies with the candidate index"):
            get_unique_new_dst(str(self.dir / "diff.txt"), 100,
                               rename_format='{stem}{suffix}')

    def test_unknown_placeholder_raises(self):
        """Unknown placeholders raise ValueError."""
        with pytest.raises(ValueError, match="Invalid rename_format"):
            get_unique_new_dst(str(self.dir / "diff.txt"), 100,
                               rename_format='{stem}_{foo}{suffix}')

    def test_malformed_template_raises(self):
        """A malformed template raises ValueError."""
        with pytest.raises(ValueError, match="Invalid rename_format"):
            get_unique_new_dst(str(self.dir / "diff.txt"), 100,
                               rename_format='{stem')

    def test_negative_rename_start_raises(self):
        """A negative rename_start raises ValueError."""
        with pytest.raises(ValueError, match="rename_start"):
            get_unique_new_dst(str(self.dir / "diff.txt"), 100,
                               rename_start=-1)

    def test_non_int_rename_start_raises(self):
        """A non-int rename_start raises TypeError."""
        with pytest.raises(TypeError, match="rename_start"):
            get_unique_new_dst(str(self.dir / "diff.txt"), 100,
                               rename_start='1')

    def test_exhaustion_raises_runtime_error(self):
        """RuntimeError is raised when every candidate is occupied."""
        for i in range(5):
            (self.dir / f"diff_{i}.txt").write_text("occupied")

        with pytest.raises(RuntimeError, match="can not be found"):
            get_unique_new_dst(str(self.dir / "diff.txt"), 5)


class TestDryRunSession:
    """dry_run_session()：一批 dry-run 调用共享"虚拟已创建目录"状态，
    使 Create directory 报告与对应的真实运行一致。"""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.src = tmp_path / "src.txt"
        self.src.write_text("content")
        self.base = tmp_path / "base"
        yield

    def _dry_copy(self, dst, **kwargs):
        copy(str(self.src), str(dst), dry_run=True, run_log=True, **kwargs)

    def test_session_reports_create_dir_once(self, capsys):
        """同一目录在会话内只报告一次创建"""
        with dry_run_session():
            self._dry_copy(self.base / "sub" / "a.txt", make_dir=True)
            self._dry_copy(self.base / "sub" / "b.txt", make_dir=True)

        out = capsys.readouterr().out
        assert out.count("Create directory") == 1
        assert out.count("[dry-run] Copied") == 2

    def test_without_session_each_call_repeats_create_dir(self, capsys):
        """无会话时保持原行为：每次调用都基于磁盘状态重复报告"""
        self._dry_copy(self.base / "sub" / "a.txt", make_dir=True)
        self._dry_copy(self.base / "sub" / "b.txt", make_dir=True)

        out = capsys.readouterr().out
        assert out.count("Create directory") == 2

    def test_session_remembers_missing_ancestors(self, capsys):
        """makedirs 会创建整条祖先链；会话记住后，落到祖先目录内不再报告，
        更深的新目录仍正常报告（与真实运行一致）"""
        with dry_run_session():
            # 虚拟创建 base/x 与 base/x/y
            self._dry_copy(self.base / "x" / "y" / "a.txt", make_dir=True)
            # base/x 已虚拟存在 -> 不报告
            self._dry_copy(self.base / "x" / "b.txt", make_dir=True)
            # base/x/z 仍缺失 -> 报告
            self._dry_copy(self.base / "x" / "z" / "c.txt", make_dir=True)

        out = capsys.readouterr().out
        assert out.count("Create directory") == 2

    def test_session_virtual_dir_satisfies_make_dir_false(self, capsys):
        """make_dir=False 的后续调用把虚拟目录视为存在，不再抛
        FileNotFoundError（真实运行中该目录已被前一次调用创建）"""
        with dry_run_session():
            self._dry_copy(self.base / "v" / "a.txt", make_dir=True)
            self._dry_copy(self.base / "v" / "b.txt", make_dir=False)

        out = capsys.readouterr().out
        assert out.count("Create directory") == 1
        assert out.count("[dry-run] Copied") == 2

    def test_real_run_ignores_session_state(self, capsys):
        """真实运行不查会话：以磁盘为准正常创建、不重复报告"""
        with dry_run_session():
            self._dry_copy(self.base / "r" / "a.txt", make_dir=True)  # 仅虚拟创建
            copy(str(self.src), str(self.base / "r" / "b.txt"),
                 make_dir=True, run_log=True)  # 真实创建
            copy(str(self.src), str(self.base / "r" / "c.txt"),
                 make_dir=True, run_log=True)  # 磁盘已存在 -> 不报告

        out = capsys.readouterr().out
        assert out.count("Create directory") == 2  # 虚拟一次 + 真实一次
        assert (self.base / "r" / "b.txt").exists()
        assert (self.base / "r" / "c.txt").exists()

    def test_move_uses_session_too(self, capsys):
        """move 与 copy 共享同一会话状态"""
        with dry_run_session():
            self._dry_copy(self.base / "m" / "a.txt", make_dir=True)
            move(str(self.src), str(self.base / "m" / "b.txt"),
                 dry_run=True, make_dir=True, run_log=True)

        out = capsys.readouterr().out
        assert out.count("Create directory") == 1
        assert "[dry-run] Moved" in out
