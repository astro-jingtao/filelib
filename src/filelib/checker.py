"""
File comparison utilities for checking if files and folders are identical.
"""

from __future__ import annotations

from collections.abc import Callable
import hashlib
from pathlib import Path

from filelib.scanner import ls


def is_same_file(file1: str | Path, file2: str | Path, mode: str = "hash") -> bool:
    """
    Check if two files are identical.

    Parameters
    ----------
    file1 : str | Path
        Path to the first file.
    file2 : str | Path
        Path to the second file.
    mode : {'hash', 'full'}, optional
        Comparison mode:
        * 'hash': Compare files using SHA256 hash (faster for large files).
        * 'full': Compare files byte-by-byte (slower but complete comparison).
        Defaults to 'hash'.

    Returns
    -------
    bool
        True if files are identical, False otherwise.

    Raises
    ------
    FileNotFoundError
        If either file does not exist.
    ValueError
        If mode is not 'hash' or 'full'.
    """
    if mode not in ("hash", "full"):
        raise ValueError(f"mode must be 'hash' or 'full', got {mode!r}")

    file1_path = Path(file1)
    file2_path = Path(file2)

    if not file1_path.exists():
        raise FileNotFoundError(f"File not found: {file1_path}")
    if not file2_path.exists():
        raise FileNotFoundError(f"File not found: {file2_path}")

    if mode == "hash":
        return _compare_by_hash(file1_path, file2_path)
    # mode == 'full'
    return _compare_full(file1_path, file2_path)


def _compare_by_hash(file1: Path, file2: Path) -> bool:
    """Compare two files using SHA256 hash."""

    def get_file_hash(filepath: Path) -> str:
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    return get_file_hash(file1) == get_file_hash(file2)


def _compare_full(file1: Path, file2: Path) -> bool:
    """Compare two files byte-by-byte."""
    with open(file1, "rb") as f1, open(file2, "rb") as f2:
        while True:
            chunk1 = f1.read(4096)
            chunk2 = f2.read(4096)
            if chunk1 != chunk2:
                return False
            if not chunk1:
                return True


def is_same_folder(
    folder1: str | Path,
    folder2: str | Path,
    *,
    file_selector_func: Callable[[str], bool] | None = None,
    file_compare_mode: str = "hash",
    compare_func: Callable[[Path, Path], bool] | None = None,
    report: bool = False,
) -> bool:
    """
    Check if two folders contain the same files with identical content.

    Parameters
    ----------
    folder1 : str | Path
        Path to the first folder.
    folder2 : str | Path
        Path to the second folder.
    file_selector_func : callable, optional
        A function that takes a file name (str) as input and returns True if the file
        should be included in the comparison. If None, all files are compared.
    file_compare_mode : {'hash', 'full'}, optional
        Comparison mode to use for individual files. Defaults to 'hash'.
    compare_func : callable, optional
        Custom file comparison function with signature ``compare_func(file1, file2)``.
        If provided, it takes precedence over ``file_compare_mode`` and
        ``is_same_file``.
    report : bool, optional
        If True, print the differences found (missing files, differing
        files) before returning False. Defaults to False.

    Returns
    -------
    bool
        True if folders contain the same files with identical content, False otherwise.

    Raises
    ------
    FileNotFoundError
        If either folder does not exist.
    ValueError
        If a path is not a directory.
    """
    folder1_path = Path(folder1)
    folder2_path = Path(folder2)

    _validate_folder(folder1_path)
    _validate_folder(folder2_path)

    # Get file lists from both folders
    files1 = _get_folder_files(folder1_path, file_selector_func)
    files2 = _get_folder_files(folder2_path, file_selector_func)

    # Check if file names and counts match
    if set(files1.keys()) != set(files2.keys()):
        if report:
            print(f"Folder {folder1_path} and {folder2_path} have different files")
            print(f"Files in {folder1_path}: {files1.keys()}")
            print(f"Files in {folder2_path}: {files2.keys()}")
        return False

    diff_files = _compare_files(files1, files2, compare_func, file_compare_mode)

    if diff_files:
        if report:
            for file1_path, file2_path in diff_files.values():
                print(f"Files {file1_path} and {file2_path} are different")
        return False

    return True


def _validate_folder(folder_path: Path) -> None:
    """Raise FileNotFoundError / ValueError unless ``folder_path`` is an
    existing directory."""
    if not folder_path.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    if not folder_path.is_dir():
        raise ValueError(f"Not a directory: {folder_path}")


def _compare_files(
    files1: dict[str, Path],
    files2: dict[str, Path],
    compare_func: Callable[[Path, Path], bool] | None,
    file_compare_mode: str,
) -> dict[str, tuple[Path, Path]]:
    """Compare the shared entries of two file lists; return the failures.

    ``compare_func`` (custom comparator) takes precedence over
    ``is_same_file`` driven by ``file_compare_mode``. The returned dict
    maps each failing relative path to its ``(folder1, folder2)`` paths.
    """
    diff_files = {}

    for filename, file1_path in files1.items():
        file2_path = files2[filename]
        if compare_func is not None:
            same = compare_func(file1_path, file2_path)
        else:
            same = is_same_file(file1_path, file2_path, mode=file_compare_mode)
        if not same:
            diff_files[filename] = (file1_path, file2_path)

    return diff_files


def _get_folder_files(
    folder: Path, file_selector_func: Callable[[str], bool] | None = None
) -> dict[str, Path]:
    """
    Get all files in a folder that match the filter function.

    Uses scanner.ls for consistent directory traversal across the package.

    Parameters
    ----------
    folder : Path
        The folder to scan.
    file_selector_func : callable, optional
        Filter function. If None, all files are included.

    Returns
    -------
    dict
        Dictionary mapping relative file paths to absolute file paths.
    """
    files = {}
    file_paths = ls(
        directory=str(folder),
        match_func=file_selector_func,
        recursive=True,
        path_type="rel_path",
        on_duplicates="ignore",
    )
    for rel_path_str in file_paths:
        abs_path = folder / rel_path_str
        files[rel_path_str] = abs_path
    return files
