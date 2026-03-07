import warnings
import os

def ls(directory=".",
       match_func=None,
       recursive=False,
       path_type='abs_full_path',
       on_duplicates="raise"):
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
        Defaults to 'file_only'.
    on_duplicates : {'raise', 'warn', 'ignore'}, optional
        Determines the behavior when duplicate file names are found:
        * 'raise': Raises a ValueError.
        * 'warn': Warns the user with a UserWarning.
        * 'ignore': Ignores the duplicates.

    Returns
    -------
    list of str
        A sorted list of file names or paths that match the criteria.

    Examples
    --------
    >>> ls(match_func=lambda f: f.endswith(('.jpg', '.gif')), recursive=True)
    ['/path/to/img1.jpg', '/path/to/subdir/img2.gif']
    """

    result = []

    # os.walk yields a 3-tuple (dirpath, dirnames, filenames)
    for root, dirs, files in os.walk(directory):
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
            elif on_duplicates == "warn":
                warnings.warn(msg, UserWarning)
            else:
                raise NotImplementedError(
                    "on_duplicates option must be one of 'raise', 'warn', or 'ignore'."
                )

    return sorted(result)

def is_empty_dir(directory):
    ...