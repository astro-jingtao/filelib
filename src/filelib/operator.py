import os
import shutil
from pathlib import Path


def move(src,
         dst,
         copy_function=None,
         dry_run=False,
         exist_policy='default',
         make_dir=False):

    dst = _check_exist_when_move(dst, exist_policy)

    _check_dir_when_move(dst, make_dir)

    if dry_run:
        print(f"[dry-run] Move {src} to {dst}")
    else:
        if copy_function is None:
            shutil.move(src, dst)
        else:
            shutil.move(src, dst, copy_function=copy_function)


def _check_dir_when_move(dst, make_dir):
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
