import os
import shutil
from pathlib import Path

# TODO: verbose option for print

def remove(path, recursive=False, dry_run=False):
    """
    删除文件或目录。

    Args:
        path (str): 要删除的文件或文件夹路径。
        recursive (bool or str): 控制非空文件夹的行为。
            True  : 连带内容一同删除 (默认行为，使用 shutil.rmtree)。
            False : 如果文件夹非空，则报错。
            'skip': 如果文件夹非空，则跳过不删除。
        dry_run (bool): 如果为 True，仅打印将要执行的操作，不实际删除。
    """
    if not os.path.exists(path):
        print(f"Warning: Path does not exist, skipping: {path}")
        return

    is_dir = os.path.isdir(path)

    # 如果是文件夹，需要检查是否非空以应对 recursive=False 或 'skip' 的情况
    if is_dir:
        is_empty = not os.listdir(path)

        # 处理非空文件夹的逻辑
        if not is_empty:
            if recursive == 'skip':
                if dry_run:
                    print(f"[dry-run] Skip non-empty directory: {path}")
                return

            if recursive is False:
                # 模拟 os.rmdir 的行为，直接抛出异常
                raise OSError(f"[Error] Directory not empty: '{path}'")

    # Dry Run 打印逻辑
    if dry_run:
        # 走到这里意味着操作将会执行
        if is_dir:
            # 只有 recursive=True 时才会真正打印 "Remove"，
            # 否则如果是空文件夹，recursive参数不影响结果，也可以打印 Remove
            print(f"[dry-run] Remove directory: {path}")
        else:
            print(f"[dry-run] Remove file: {path}")
        return

    # 实际执行逻辑
    if is_dir:
        if recursive is True or recursive == 'skip':
            # 'skip' 情况下如果能走到这，说明文件夹是空的，正常删除即可
            # True 情况下，无论是否为空都强制删除
            shutil.rmtree(path)
        else:
            # recursive=False 且文件夹为空的情况
            os.rmdir(path)
    else:
        os.remove(path)


def move(src,
         dst,
         copy_function=None,
         dry_run=False,
         exist_policy='default',
         make_dir=False):

    dst = _check_exist_when_move(dst, exist_policy)

    _check_dir_when_move(dst, make_dir, dry_run=dry_run)

    if dry_run:
        print(f"[dry-run] Move {src} to {dst}")
    else:
        if copy_function is None:
            shutil.move(src, dst)
        else:
            shutil.move(src, dst, copy_function=copy_function)


def _check_dir_when_move(dst, make_dir, dry_run=False):
    """ check if the parent folder of dst exist, if not, create it or raise error

    Parameters
    ----------
    dst : str
        destination path
    make_dir : bool
        if True, create the parent folder of dst if not exist, otherwise raise error
    """

    dst_folder = os.path.dirname(dst)
    if not os.path.exists(dst_folder):
        if make_dir:
            if dry_run:
                print(f"[dry-run] Create directory {dst_folder}")
            else:
                os.makedirs(dst_folder, exist_ok=False)
        else:
            raise FileNotFoundError(
                f"Parent folder {dst_folder} of destination {dst} does not exist."
            )


def _check_exist_when_move(dst, exist_policy):
    """ check if dst already exist and deal with it according to `exist_policy`

    Parameters
    ----------
    dst : str
        destination path
    exist_policy : str
        'default' (do nothing), 'overwrite' (remove existing file), 'rename' (add suffix to existing file)
    """

    MAX_TRY = 10000

    if (exist_policy
            == 'default') or os.path.isdir(dst) or not os.path.exists(dst):
        return dst

    # Now a file exist
    if exist_policy == 'overwrite':
        os.remove(dst)
        return dst
    elif exist_policy == 'rename':
        dst_new = get_unique_new_dst(dst, MAX_TRY)
        return dst_new
    else:
        raise ValueError(
            "exist_policy must be 'default', 'overwrite' or 'rename'")


def get_unique_new_dst(dst, MAX_TRY):
    dst_path = Path(dst)
    dst_new = dst_path.with_suffix('').as_posix() + '_0' + dst_path.suffix
    for i in range(1, MAX_TRY):
        if not os.path.exists(dst_new):
            break
        dst_new = dst_path.with_suffix(
            '').as_posix() + f'_{i}' + dst_path.suffix
    else:
        raise RuntimeError(
            f'{dst} already exists, and new name can not be found with {MAX_TRY} try'
        )

    return dst_new
