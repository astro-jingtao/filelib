# pylint: disable=attribute-defined-outside-init

import pytest
import filelib.operator as operator_module
from filelib.operator import copy, move, remove


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
