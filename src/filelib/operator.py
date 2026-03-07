import os
import shutil
from pathlib import Path
from filelib.printer import Printer


def remove(path, recursive=False, dry_run=False, run_log=False):
    """
    删除文件或目录。

    Args:
        path (str): 要删除的文件或文件夹路径。
        recursive (bool or str): 控制非空文件夹的行为。
            True  : 连带内容一同删除 (默认行为，使用 shutil.rmtree)。
            False : 如果文件夹非空，则报错。
            'skip': 如果文件夹非空，则跳过不删除。
        dry_run (bool): 如果为 True，仅打印将要执行的操作，不实际删除。
        run_log (bool): 如果为 True，在执行操作时打印详细信息。
    """

    printer = Printer(dry_run=dry_run, run_log=run_log, ignore_warning=False)

    if not os.path.exists(path):
        printer.print_warning(f"Path does not exist, skipping: {path}")
        return

    is_dir = os.path.isdir(path)

    # 如果是文件夹，需要检查是否非空以应对 recursive=False 或 'skip' 的情况
    if is_dir:
        is_empty = not os.listdir(path)

        # 处理非空文件夹的逻辑
        if not is_empty:
            if recursive == 'skip':
                printer.print_general_run_log(
                    f"Skipped non-empty directory: {path}")
                return
            if recursive is False:
                # 模拟 os.rmdir 的行为，直接抛出异常
                raise OSError(f"[Error] Directory not empty: '{path}'")

        # 实际操作
        if recursive is True or recursive == 'skip':
            # 'skip' 情况下如果能走到这，说明文件夹是空的，正常删除即可
            # True 情况下，无论是否为空都强制删除
            if not dry_run:
                shutil.rmtree(path)
            printer.print_general_run_log(f"Removed directory: {path}")
        else:
            # recursive=False 且文件夹为空的情况
            if not dry_run:
                os.rmdir(path)
            printer.print_general_run_log(f"Removed empty directory: {path}")
    else:
        if not dry_run:
            os.remove(path)
        printer.print_general_run_log(f"Removed file: {path}")


def move(src,
         dst,
         copy_function=None,
         dry_run=False,
         exist_policy='default',
         make_dir=False,
         run_log=False):

    printer = Printer(dry_run=dry_run, run_log=run_log, ignore_warning=False)

    dst = _check_dst_exist(dst, exist_policy, dry_run, printer)

    _check_dst_parent_folder_exist(dst, make_dir, dry_run, printer)

    if not dry_run:
        if copy_function is None:
            shutil.move(src, dst)
        else:
            shutil.move(src, dst, copy_function=copy_function)

    printer.print_general_run_log(f"Moved {src} to {dst}")


def copy(src,
         dst,
         copy_function=None,
         dry_run=False,
         exist_policy='default',
         make_dir=False,
         run_log=False):
    # TODO: if -r 

    printer = Printer(dry_run=dry_run, run_log=run_log, ignore_warning=False)

    dst = _check_dst_exist(dst, exist_policy, dry_run, printer)

    _check_dst_parent_folder_exist(dst, make_dir, dry_run, printer)

    if not dry_run:
        if os.path.isdir(src):
            if copy_function is None:
                shutil.copytree(src, dst)
            else:
                shutil.copytree(src, dst, copy_function=copy_function)
        else:
            if copy_function is None:
                shutil.copy2(src, dst)
            else:
                copy_function(src, dst)

    printer.print_general_run_log(f"Copied {src} to {dst}")


def _check_dst_parent_folder_exist(dst, make_dir, dry_run, printer: Printer):
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
            if not dry_run:
                os.makedirs(dst_folder, exist_ok=False)
            printer.print_general_run_log(f"Create directory {dst_folder}")
        else:
            raise FileNotFoundError(
                f"Parent folder {dst_folder} of destination {dst} does not exist."
            )


def _check_dst_exist(dst, exist_policy, dry_run, printer: Printer):
    """ check if dst already exist and deal with it according to `exist_policy`

    Parameters
    ----------
    dst : str
        destination path
    exist_policy : str
        'default' (do nothing), 'overwrite' (remove existing file), 'rename' (add suffix to existing file)
    dry_run : bool
        if True, only print the operation without actually doing it
    printer : Printer
        printer object for logging
    """

    MAX_TRY = 10000

    if (exist_policy
            == 'default') or os.path.isdir(dst) or not os.path.exists(dst):
        return dst

    # Now a file exist
    if exist_policy == 'overwrite':
        if not dry_run:
            os.remove(dst)
        printer.print_general_run_log(f"Removed existing file: {dst}")
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
