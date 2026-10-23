import os
import warnings


def ls(directory=".",
       match_func=None,
       recursive=False,
       path_type='abs_full_path',
       on_duplicates="raise",
       follow_symlinks=True):
    """
    List files in a directory, similar to the shell 'ls' command, with support for custom filtering and path formatting.

    Parameters
    ----------
    directory : str, optional
        The root directory to search in. Defaults to the current directory (".").
    match_func : callable, optional
        A function that takes a file name (str) as input and returns True if the file
        should be included in the result. If None, all files are returned.
    recursive : bool, optional
        If True, performs a recursive search through subdirectories. Defaults to False.
    path_type : {'file_only', 'raw_full_path', 'abs_full_path', 'rel_path'}, optional
        Determines the format of the returned file paths:
        * 'file_only': Returns only the filename (e.g., 'data.csv').
        * 'raw_full_path': Returns the path as concatenated during traversal.
        * 'abs_full_path': Returns the absolute system path.
        * 'rel_path': Returns the path relative to the input `directory`.
        Defaults to 'abs_full_path'.
    on_duplicates : {'raise', 'warn', 'ignore'}, optional
        Determines the behavior when duplicate file names are found:
        * 'raise': Raises a ValueError.
        * 'warn': Warns the user with a UserWarning.
        * 'ignore': Ignores the duplicates.
        Any other value raises a ValueError before scanning starts.
    follow_symlinks : bool, optional
        If True, recursive directory traversal follows symbolic links to
        directories. If False, symlinked directories are not traversed.
        Defaults to True.

    Returns
    -------
    list of str
        A sorted list of file names or paths that match the criteria.

    Raises
    ------
    ValueError
        If ``on_duplicates`` is not one of 'raise', 'warn', 'ignore'
        (checked before scanning starts); if ``path_type`` is invalid
        (raised when the first file is reached); or if duplicate file
        names are found in 'file_only' mode with ``on_duplicates='raise'``.

    Examples
    --------
    >>> ls(match_func=lambda f: f.endswith(('.jpg', '.gif')), recursive=True)
    ['/path/to/img1.jpg', '/path/to/subdir/img2.gif']
    """

    # 非法枚举值在扫描开始前即拒绝：与包内其他参数校验（ValueError）一致，
    # 且不依赖"是否恰好存在重复名"才暴露。
    if on_duplicates not in ("raise", "warn", "ignore"):
        raise ValueError(
            f"Invalid on_duplicates: {on_duplicates}. "
            "Choose from 'raise', 'warn', or 'ignore'."
        )

    result = []

    # os.walk yields a 3-tuple (dirpath, dirnames, filenames)
    for root, dirs, files in os.walk(directory, followlinks=follow_symlinks):
        for file in files:
            # Extension filtering logic
            if match_func and not match_func(file):
                continue

            # Path construction logic
            if path_type == "abs_full_path":
                p = os.path.abspath(os.path.join(root, file))
            elif path_type == "raw_full_path":
                p = os.path.join(root, file)
            elif path_type == "rel_path":
                # 返回相对于初始 directory 的路径
                p = os.path.relpath(os.path.join(root, file), directory)
            elif path_type == "file_only":
                p = file
            else:
                raise ValueError(
                    f"Invalid path_type: {path_type}. "
                    "Choose from 'raw_full_path', 'abs_full_path', 'rel_path', 'file_only'."
                )

            result.append(p)

        # Stop after the first level if recursive is False
        if not recursive:
            break

    # check if same file name in result when path_type is 'file_only'
    if (path_type == 'file_only') and (on_duplicates != 'ignore'):
        if len(result) != len(set(result)):
            msg = (
                "Duplicate file names found in 'file_only' mode. "
                "Consider using 'rel_path', 'raw_full_path', or 'abs_full_path' for unique paths."
            )
            if on_duplicates == "raise":
                raise ValueError(msg)
            # 只剩 'warn'（非法值已在入口拒绝）
            warnings.warn(msg, UserWarning)

    return sorted(result)


def is_empty_dir(directory, recursive=False):
    """
    Check whether a directory is empty.

    Parameters
    ----------
    directory : str or os.PathLike
        Path to the directory to check.
    recursive : bool, optional
        If False (default), the directory is empty only when it contains no
        entries at all (files, subdirectories, and hidden entries such as
        '.gitkeep' all count as content).
        If True, the directory is considered empty when it contains no files
        at any depth, i.e. a directory holding only empty subdirectories
        (arbitrarily nested) counts as empty. Directory symlinks are followed
        (same default as ``ls()``).

    Returns
    -------
    bool
        True if the directory is empty under the chosen mode, False otherwise.

    Raises
    ------
    FileNotFoundError
        If ``directory`` does not exist.
    NotADirectoryError
        If ``directory`` exists but is not a directory.

    Examples
    --------
    >>> is_empty_dir("some/folder")            # contains only empty subdirs
    False
    >>> is_empty_dir("some/folder", recursive=True)
    True
    """
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Directory does not exist: '{directory}'")
    if not os.path.isdir(directory):
        raise NotADirectoryError(f"Not a directory: '{directory}'")

    if not recursive:
        # 浅层模式：只需要知道目录里"有没有条目"，不需要完整列表。
        # os.scandir 返回惰性迭代器，用 next(entries, None) 取第一个条目：
        #   - 取到任意条目（文件、子目录、隐藏文件都算）→ 非空，返回 False
        #   - 迭代器已耗尽、返回 None → 目录为空，返回 True
        # 相比 os.listdir 先构建完整条目列表，这里遇到第一个条目即短路返回。
        with os.scandir(directory) as entries:
            return next(entries, None) is None

    # 递归模式："空"的定义放宽为整棵子树中没有任何文件。
    # 借用 ls(directory, recursive=True) 递归枚举子树中的全部文件：
    #   - 返回空列表 → 子树里只有（可任意嵌套的）空目录 → 视为空
    #   - 返回非空列表 → 子树中至少存在一个文件 → 非空
    # 注意 ls() 默认 follow_symlinks=True，指向目录的软链接会被跟进扫描。
    return not ls(directory, recursive=True)
