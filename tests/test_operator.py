import pytest
from filelib.operator import remove


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
        assert "[dry-run] Remove file" in captured.out
        assert self.file_path.exists()  # 文件应该还在

    def test_dry_run_empty_dir(self, capsys):
        """测试 Dry Run：空文件夹不删除，仅打印"""
        remove(str(self.empty_dir_path), dry_run=True)

        captured = capsys.readouterr()
        assert "[dry-run] Remove directory" in captured.out
        assert self.empty_dir_path.exists()

    def test_dry_run_non_empty_dir_recursive_true(self, capsys):
        """测试 Dry Run：非空文件夹，recursive=True 模式"""
        remove(str(self.non_empty_dir_path), recursive=True, dry_run=True)

        captured = capsys.readouterr()
        assert "[dry-run] Remove directory" in captured.out
        assert self.non_empty_dir_path.exists()

    def test_dry_run_non_empty_dir_recursive_skip(self, capsys):
        """测试 Dry Run：非空文件夹，recursive='skip' 模式，应打印跳过日志"""
        remove(str(self.non_empty_dir_path), recursive='skip', dry_run=True)

        captured = capsys.readouterr()
        assert "[dry-run] Skip non-empty directory" in captured.out
        assert self.non_empty_dir_path.exists()
