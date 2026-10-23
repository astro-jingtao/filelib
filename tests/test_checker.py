"""
Tests for the checker module.
"""

from pathlib import Path

import pytest

from filelib.checker import is_same_file, is_same_folder


class TestIsSameFile:
    """Tests for is_same_file function."""

    @pytest.fixture
    def setup_files(self, tmp_path: Path):
        """Create test files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file3 = tmp_path / "file3.txt"

        file1.write_text("hello world")
        file2.write_text("hello world")
        file3.write_text("different content")

        return {
            'same1': file1,
            'same2': file2,
            'different': file3
        }

    def test_is_same_file_hash_mode_identical(self, setup_files):
        """Test hash mode with identical files."""
        assert is_same_file(setup_files['same1'], setup_files['same2'], mode='hash')

    def test_is_same_file_hash_mode_different(self, setup_files):
        """Test hash mode with different files."""
        assert not is_same_file(setup_files['same1'], setup_files['different'], mode='hash')

    def test_is_same_file_full_mode_identical(self, setup_files):
        """Test full mode with identical files."""
        assert is_same_file(setup_files['same1'], setup_files['same2'], mode='full')

    def test_is_same_file_full_mode_different(self, setup_files):
        """Test full mode with different files."""
        assert not is_same_file(setup_files['same1'], setup_files['different'], mode='full')

    def test_is_same_file_default_mode(self, setup_files):
        """Test that default mode is 'hash'."""
        assert is_same_file(setup_files['same1'], setup_files['same2'])

    def test_is_same_file_binary_content(self, tmp_path):
        """Test with binary files."""
        binary1 = tmp_path / "binary1.bin"
        binary2 = tmp_path / "binary2.bin"

        binary_data = b'\x00\x01\x02\x03\x04\x05'
        binary1.write_bytes(binary_data)
        binary2.write_bytes(binary_data)

        assert is_same_file(binary1, binary2, mode='hash')
        assert is_same_file(binary1, binary2, mode='full')

    def test_is_same_file_large_file(self, tmp_path):
        """Test with large files."""
        large1 = tmp_path / "large1.bin"
        large2 = tmp_path / "large2.bin"

        large_data = b'x' * (10 * 1024 * 1024)  # 10 MB
        large1.write_bytes(large_data)
        large2.write_bytes(large_data)

        assert is_same_file(large1, large2, mode='hash')

    def test_is_same_file_file_not_found(self, tmp_path):
        """Test with non-existent file."""
        existing = tmp_path / "existing.txt"
        existing.write_text("content")
        nonexistent = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            is_same_file(existing, nonexistent)

    def test_is_same_file_invalid_mode(self, setup_files):
        """Test with invalid mode."""
        with pytest.raises(ValueError, match="mode must be 'hash' or 'full'"):
            is_same_file(setup_files['same1'], setup_files['same2'], mode='invalid')

    def test_is_same_file_with_pathlib(self, setup_files):
        """Test with pathlib.Path objects."""
        assert is_same_file(setup_files['same1'], setup_files['same2'])

    def test_is_same_file_with_string_paths(self, setup_files):
        """Test with string paths."""
        assert is_same_file(str(setup_files['same1']), str(setup_files['same2']))


class TestIsSameFolder:
    """Tests for is_same_folder function."""

    @pytest.fixture
    def setup_folders(self, tmp_path: Path):
        """Create test folders with files."""
        folder1 = tmp_path / "folder1"
        folder2 = tmp_path / "folder2"
        folder3 = tmp_path / "folder3"

        folder1.mkdir()
        folder2.mkdir()
        folder3.mkdir()

        # Create identical structure in folder1 and folder2
        (folder1 / "file1.txt").write_text("content1")
        (folder1 / "file2.txt").write_text("content2")
        (folder1 / "subdir").mkdir()
        (folder1 / "subdir" / "file3.txt").write_text("content3")

        (folder2 / "file1.txt").write_text("content1")
        (folder2 / "file2.txt").write_text("content2")
        (folder2 / "subdir").mkdir()
        (folder2 / "subdir" / "file3.txt").write_text("content3")

        # Create different structure in folder3
        (folder3 / "file1.txt").write_text("content1")
        (folder3 / "file2.txt").write_text("different")

        return {
            'same1': folder1,
            'same2': folder2,
            'different': folder3
        }

    def test_is_same_folder_identical(self, setup_folders):
        """Test with identical folders."""
        assert is_same_folder(setup_folders['same1'], setup_folders['same2'])

    def test_is_same_folder_different_content(self, setup_folders):
        """Test with folders having different content."""
        assert not is_same_folder(setup_folders['same1'], setup_folders['different'])

    def test_is_same_folder_empty_folders(self, tmp_path):
        """Test with empty folders."""
        empty1 = tmp_path / "empty1"
        empty2 = tmp_path / "empty2"
        empty1.mkdir()
        empty2.mkdir()

        assert is_same_folder(empty1, empty2)

    def test_is_same_folder_different_files(self, tmp_path):
        """Test with folders having different file counts."""
        folder1 = tmp_path / "folder1"
        folder2 = tmp_path / "folder2"
        folder1.mkdir()
        folder2.mkdir()

        (folder1 / "file1.txt").write_text("content")
        (folder2 / "file1.txt").write_text("content")
        (folder2 / "file2.txt").write_text("content")

        assert not is_same_folder(folder1, folder2)

    def test_is_same_folder_match_func_all_files(self, setup_folders):
        """Test with match_func that accepts all files."""
        assert is_same_folder(
            setup_folders['same1'],
            setup_folders['same2'],
            file_selector_func=lambda name: True
        )

    def test_is_same_folder_match_func_filter(self, setup_folders):
        """Test with match_func that filters files."""
        # Only compare .txt files
        assert is_same_folder(
            setup_folders['same1'],
            setup_folders['same2'],
            file_selector_func=lambda name: name.endswith('.txt')
        )

    def test_is_same_folder_match_func_exclude_all(self, tmp_path):
        """Test with match_func that excludes all files."""
        folder1 = tmp_path / "folder1"
        folder2 = tmp_path / "folder2"
        folder1.mkdir()
        folder2.mkdir()

        (folder1 / "file1.txt").write_text("content1")
        (folder2 / "file1.txt").write_text("content2")

        # If we exclude all files, both folders are "same" (no files to compare)
        assert is_same_folder(
            folder1,
            folder2,
            file_selector_func=lambda name: False
        )

    def test_is_same_folder_file_compare_mode(self, setup_folders):
        """Test with different file comparison modes."""
        assert is_same_folder(
            setup_folders['same1'],
            setup_folders['same2'],
            file_compare_mode='full'
        )

    def test_is_same_folder_compare_func_priority(self, setup_folders):
        """Custom compare_func should take precedence over file_compare_mode."""
        # Keep structure identical but content different so compare_func branch is exercised.
        (setup_folders['same2'] / "file1.txt").write_text("changed")

        assert is_same_folder(
            setup_folders['same1'],
            setup_folders['same2'],
            file_compare_mode='invalid_mode',
            compare_func=lambda file1, file2: True
        )

    def test_is_same_folder_compare_func_can_fail(self, setup_folders):
        """Custom compare_func should control the comparison result."""
        # Keep structure identical but content different so compare_func can return False.
        (setup_folders['same2'] / "file2.txt").write_text("different length content")

        def compare_by_name_and_size(file1: Path, file2: Path) -> bool:
            return file1.name == file2.name and file1.stat().st_size == file2.stat().st_size

        assert not is_same_folder(
            setup_folders['same1'],
            setup_folders['same2'],
            compare_func=compare_by_name_and_size
        )

    def test_is_same_folder_not_found(self, tmp_path):
        """Test with non-existent folder."""
        existing = tmp_path / "existing"
        existing.mkdir()
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(FileNotFoundError):
            is_same_folder(existing, nonexistent)

    def test_is_same_folder_not_directory(self, tmp_path):
        """Test when path is not a directory."""
        folder = tmp_path / "folder"
        folder.mkdir()
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        with pytest.raises(ValueError, match="Not a directory"):
            is_same_folder(folder, file_path)

    def test_is_same_folder_with_pathlib(self, setup_folders):
        """Test with pathlib.Path objects."""
        assert is_same_folder(setup_folders['same1'], setup_folders['same2'])

    def test_is_same_folder_with_string_paths(self, setup_folders):
        """Test with string paths."""
        assert is_same_folder(str(setup_folders['same1']), str(setup_folders['same2']))

    def test_is_same_folder_nested_structure(self, tmp_path):
        """Test with deeply nested folder structures."""
        folder1 = tmp_path / "folder1"
        folder2 = tmp_path / "folder2"
        folder1.mkdir()
        folder2.mkdir()

        # Create nested structure
        nested1 = folder1 / "a" / "b" / "c"
        nested2 = folder2 / "a" / "b" / "c"
        nested1.mkdir(parents=True)
        nested2.mkdir(parents=True)

        (nested1 / "deep_file.txt").write_text("deep content")
        (nested2 / "deep_file.txt").write_text("deep content")

        assert is_same_folder(folder1, folder2)

    def test_is_same_folder_different_nested_files(self, tmp_path):
        """Test with different nested files."""
        folder1 = tmp_path / "folder1"
        folder2 = tmp_path / "folder2"
        folder1.mkdir()
        folder2.mkdir()

        nested1 = folder1 / "a" / "b"
        nested2 = folder2 / "a" / "b"
        nested1.mkdir(parents=True)
        nested2.mkdir(parents=True)

        (nested1 / "file.txt").write_text("content1")
        (nested2 / "file.txt").write_text("content2")

        assert not is_same_folder(folder1, folder2)
