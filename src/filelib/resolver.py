"""Path identity check through canonical resolution."""
from __future__ import annotations

from pathlib import Path


def is_same_path(path1: str | Path, path2: str | Path) -> bool:
    """True if both paths resolve to the same canonical location.

    resolve() 会处理：
    1. 相对路径转绝对路径
    2. 消除多余的斜杠 //
    3. 解析符号链接 (Symbolic links)
    4. 统一路径分隔符
    """
    p1 = Path(path1).resolve()
    p2 = Path(path2).resolve()

    return p1 == p2
