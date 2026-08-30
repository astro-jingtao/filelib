from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from filelib.checker import is_same_file
from filelib.printer import Printer
from filelib.resolver import is_same_path
from filelib.scanner import ls


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
         run_log=False,
         retarget_symlinks=False):
    """Move a file or directory from ``src`` to ``dst``.

    Wraps ``shutil.move``: same-drive moves rename, cross-drive moves
    fall back to copy + delete. Symlinks are always moved as links on
    both paths; ``retarget_symlinks`` only adds retargeting for real
    directory trees.

    Parameters
    ----------
    src : str | Path
        Source file, directory, or symlink to move.
    dst : str | Path
        Destination path. If ``dst`` is an existing directory, ``src``
        is moved into it as ``dst/<basename(src)>``.
    copy_function : callable, optional
        Passed through to ``shutil.move`` for cross-drive fallbacks.
    dry_run : bool, default False
        If True, only preview the action without touching the
        filesystem. Pre-checks (including the symlink-privilege probe)
        still run, so an infeasible move fails in the preview already.
    exist_policy : {'default', 'overwrite', 'rename'}, default 'default'
        Applied only when ``dst`` exists as a *file*. When ``dst`` is
        missing or an existing *directory*, ``exist_policy`` is
        ignored (see the table below for what happens instead).
    make_dir : bool, default False
        If True, create missing parent directories of ``dst``; if
        False, raise ``FileNotFoundError`` when they are missing.
    run_log : bool, default False
        If True, print a log line for the action and one
        ``[RETARGET]`` line per rewritten link.
    retarget_symlinks : bool, default False
        If True and ``src`` is a real directory, symlinks in the moved
        tree whose absolute targets lie inside ``src`` are rewritten
        to point at the corresponding location in the moved tree, so
        they do not dangle after the move. Relative links and links
        pointing outside the tree are kept verbatim. Single symlinks
        are never retargeted: only the link itself is moved, its target
        stays where it was (and remains valid), while a remapped target
        would point at a counterpart that was never created. Rewriting
        links requires symlink-creation privilege, which is probed
        before anything is moved.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If ``exist_policy`` is not one of ``'default'``, ``'overwrite'``,
        ``'rename'``.
    FileNotFoundError
        If the parent folder of ``dst`` does not exist and
        ``make_dir`` is False.
    PermissionError
        If ``retarget_symlinks=True`` would rewrite at least one link
        but the environment cannot create symlinks (Windows: admin
        rights or Developer Mode). Raised before any filesystem
        change, including in ``dry_run`` mode.
    FileExistsError
        If ``src`` is a symlink or a directory and ``dst`` is an
        existing file with ``exist_policy='default'`` (``os.rename``
        cannot replace it; the source is left untouched).
    shutil.Error
        If ``dst`` is an existing directory and
        ``dst/<basename(src)>`` already exists.

    Notes
    -----
    Behavior by state. "retarget" in the action column means the extra
    effect of ``retarget_symlinks=True``; every other row behaves the
    same with the flag on or off.

    +------------+------------------+--------------------+----------------------------------------+
    | src        | dst              | exist_policy       | action                                 |
    +------------+------------------+--------------------+----------------------------------------+
    | file       | missing          | ignored            | plain move                             |
    | file       | existing dir     | ignored            | moved to dst/<basename(src)>           |
    | file       | existing file    | default            | overwritten (rename / copy2 fallback)  |
    | file       | existing file    | overwrite          | existing file removed first, then      |
    |            |                  |                    | moved                                  |
    | file       | existing file    | rename             | moved to stem_0.ext (first free        |
    |            |                  |                    | suffix)                                |
    | directory  | missing          | ignored            | tree moved; retarget: in-tree absolute |
    |            |                  |                    | links rewritten                        |
    | directory  | existing dir     | ignored            | moved to dst/<basename(src)>;          |
    |            |                  |                    | shutil.Error if that path exists;      |
    |            |                  |                    | retarget: links rewritten              |
    | directory  | existing file    | default            | error (a directory cannot be moved     |
    |            |                  |                    | onto a file)                           |
    | directory  | existing file    | overwrite / rename | existing file removed / suffix added,  |
    |            |                  |                    | then moved; retarget applies           |
    | symlink    | missing          | ignored            | moved as a link, never retargeted      |
    | symlink    | existing dir     | ignored            | moved to dst/<basename(src)> as a      |
    |            |                  |                    | link; shutil.Error if that path exists |
    | symlink    | existing file    | default            | FileExistsError (rename cannot replace |
    |            |                  |                    | a file with a link; link left in place)|
    | symlink    | existing file    | overwrite          | existing file removed first, then      |
    |            |                  |                    | moved as a link                        |
    | symlink    | existing file    | rename             | link moved to stem_0.ext, never        |
    |            |                  |                    | retargeted                             |
    +------------+------------------+--------------------+----------------------------------------+

    * ``dry_run=True`` prints ``[dry-run] [RETARGET] <link>: <old> ->
      <new>`` for every link that would be rewritten.
    * Links are preserved by the move itself regardless of
      ``retarget_symlinks``; the flag only decides whether absolute
      in-tree targets are fixed up afterwards.
    """

    printer = Printer(dry_run=dry_run, run_log=run_log, ignore_warning=False)

    dst = _check_dst_exist(dst, exist_policy, dry_run, printer)

    _check_dst_parent_folder_exist(dst, make_dir, dry_run, printer)

    # Capture before shutil.move consumes them: an existing dst directory
    # makes the tree land at dst/basename(src), and the source is gone
    # after a same-drive move.
    dst_is_dir = os.path.isdir(dst)
    src_is_link = os.path.islink(src)
    src_is_dir = os.path.isdir(src)
    land_root = (os.path.join(dst, os.path.basename(src)) if dst_is_dir
                 else dst)

    # privilege pre-check: the move itself preserves links without extra
    # rights; only the retarget pass rewrites them, and only if at least
    # one link target would actually change
    if retarget_symlinks and src_is_dir and not src_is_link:
        src_abs = os.path.abspath(src)
        land_abs = os.path.abspath(land_root)
        if any(True for _ in _iter_retargets(src_abs, src_abs, land_abs)):
            _check_symlink_privilege()

    if not dry_run:
        if copy_function is None:
            shutil.move(src, dst)
        else:
            shutil.move(src, dst, copy_function=copy_function)

    if retarget_symlinks and src_is_dir and not src_is_link:
        _retarget_symlinks(src, land_root, dry_run, printer)

    printer.print_general_run_log(f"Moved {src} to {dst}")


def copy(src,
         dst,
         copy_function=None,
         dry_run=False,
         exist_policy='default',
         make_dir=False,
         run_log=False,
         preserve_symlinks=False,
         retarget_symlinks=False):
    """Copy a file or directory from ``src`` to ``dst``.

    Files are copied with ``shutil.copy2`` (metadata included) and
    directories with ``shutil.copytree``; ``copy_function`` overrides
    the per-file copier. By default symlinks are followed.
    ``preserve_symlinks=True`` keeps them as links, and
    ``retarget_symlinks=True`` (requires ``preserve_symlinks=True``)
    additionally rewrites absolute in-tree link targets in the copy.

    Parameters
    ----------
    src : str | Path
        Source file, directory, or symlink to copy.
    dst : str | Path
        Destination path. If ``dst`` is an existing directory, ``src``
        is copied into it as ``dst/<basename(src)>``.
    copy_function : callable, optional
        Per-file copy function used instead of ``shutil.copy2`` (also
        passed through to ``shutil.copytree``).
    dry_run : bool, default False
        If True, only preview the action without touching the
        filesystem. Pre-checks (including the symlink-privilege probe)
        still run, so an infeasible copy fails in the preview already.
    exist_policy : {'default', 'overwrite', 'rename'}, default 'default'
        Applied only when ``dst`` exists as a *file*. When ``dst`` is
        missing or an existing *directory*, ``exist_policy`` is
        ignored (see the table below for what happens instead).
    make_dir : bool, default False
        If True, create missing parent directories of ``dst``; if
        False, raise ``FileNotFoundError`` when they are missing.
    run_log : bool, default False
        If True, print a log line for the action and one
        ``[RETARGET]`` line per rewritten link.
    preserve_symlinks : bool, default False
        If True, symlinks are copied as symlinks instead of being
        followed: a symlink ``src`` is recreated at ``dst`` with its
        original target, and symlinks inside a directory tree are
        recreated as links. Creating them requires symlink-creation
        privilege, which is probed before anything is copied.
    retarget_symlinks : bool, default False
        If True (together with ``preserve_symlinks=True``), links in
        the copy whose absolute targets lie inside ``src`` are
        rewritten to the corresponding location in the copy. Used
        without ``preserve_symlinks=True`` a warning is printed and
        nothing is retargeted.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If ``exist_policy`` is not one of ``'default'``, ``'overwrite'``,
        ``'rename'``.
    FileNotFoundError
        If the parent folder of ``dst`` does not exist and
        ``make_dir`` is False.
    PermissionError
        If ``preserve_symlinks=True`` would create or rewrite at least
        one link but the environment cannot create symlinks (Windows:
        admin rights or Developer Mode). Raised before any filesystem
        change, including in ``dry_run`` mode.
    FileExistsError
        If ``dst`` exists with ``exist_policy='default'`` and a
        directory ``src`` (from ``copytree``), or if a symlink is
        recreated onto an existing file with
        ``preserve_symlinks=True`` (plain ``copy2`` would overwrite).
    shutil.Error
        If ``shutil.copytree`` encounters errors (e.g. dangling
        symlinks inside a tree copied without ``preserve_symlinks``).

    Notes
    -----
    Behavior by state. ``exist_policy`` applies only to the rows that
    name it; on every other row it is ignored.

    +------------+------------------+------------------+--------------------------------------+
    | src        | dst              | exist_policy     | action                               |
    +------------+------------------+------------------+--------------------------------------+
    | file       | missing          | ignored          | copied (copy2)                       |
    | file       | existing dir     | ignored          | copied to dst/<basename(src)>        |
    | file       | existing file    | default          | silently overwritten by copy2        |
    | file       | existing file    | overwrite        | existing file removed first, then    |
    |            |                  |                  | copied                               |
    | file       | existing file    | rename           | copied to stem_0.ext (first free     |
    |            |                  |                  | suffix)                              |
    | directory  | missing          | ignored          | copytree; see the flags table below  |
    | directory  | existing file    | default          | FileExistsError (copytree)           |
    | directory  | existing file    | overwrite        | existing file removed, then copytree |
    | directory  | existing file    | rename           | copytree to stem_0.ext               |
    | directory  | existing dir     | ignored          | FileExistsError (copytree)           |
    | symlink    | missing          | ignored          | see the flags table below            |
    | symlink    | existing dir     | ignored          | copied to dst/<basename(src)>;       |
    |            |                  |                  | link/followed per flags table        |
    | symlink    | existing file    | default          | flags off: dst overwritten with      |
    |            |                  |                  | target content; preserve on:         |
    |            |                  |                  | FileExistsError                      |
    | symlink    | existing file    | overwrite        | existing file removed first, then    |
    |            |                  |                  | per flags table                      |
    | symlink    | existing file    | rename           | stem_0.ext, then per flags table     |
    +------------+------------------+------------------+--------------------------------------+

    Effect of the symlink flags:

    +------------+---------------------------+--------------------------------------+
    | src        | flags                     | action                               |
    +------------+---------------------------+--------------------------------------+
    | symlink    | default (both off)        | followed: the target's content is    |
    |            |                           | copied (copy2 follows symlinks);     |
    |            |                           | directory links become real          |
    |            |                           | directories                          |
    | symlink    | preserve_symlinks=True    | recreated as a link with the         |
    |            |                           | original target (into dst when dst   |
    |            |                           | is a directory); never retargeted    |
    | directory  | default (both off)        | inner links followed (copytree       |
    |            |                           | default; dangling links raise)       |
    | directory  | preserve_symlinks=True    | inner links kept as links, original  |
    |            |                           | targets unchanged                    |
    | directory  | preserve + retarget=True  | inner links kept as links; absolute  |
    |            |                           | in-tree targets rewritten to the     |
    |            |                           | copy                                 |
    +------------+---------------------------+--------------------------------------+

    * ``retarget_symlinks=True`` without ``preserve_symlinks=True``
      prints a warning and does nothing (links are followed).
    * Single symlinks are never retargeted: only the link is
      copied/moved, its target stays where it was (and remains valid),
      while a remapped target would point at a counterpart that was
      never created — retargeting is only sound when the whole tree
      containing both the link and its target is transported.
    * ``dry_run=True`` prints ``[dry-run] [RETARGET] <link>: <old> ->
      <new>`` for every link that would be rewritten.
    """
    # TODO: if -r

    printer = Printer(dry_run=dry_run, run_log=run_log, ignore_warning=False)

    dst = _check_dst_exist(dst, exist_policy, dry_run, printer)

    _check_dst_parent_folder_exist(dst, make_dir, dry_run, printer)

    # islink must be checked before isdir (isdir follows symlinks)
    src_is_link = os.path.islink(src)
    src_is_dir = os.path.isdir(src)

    # retargeting without preservation is meaningless: warn and disable
    if retarget_symlinks and not preserve_symlinks:
        printer.print_warning(
            'retarget_symlinks=True has no effect without '
            'preserve_symlinks=True; symlinks are followed and nothing '
            'is retargeted.')
        retarget_symlinks = False

    # privilege pre-check: probe before touching dst, so a missing right
    # fails the call up front instead of halfway through the copy
    if preserve_symlinks:
        src_abs = os.path.abspath(src)
        if src_is_link or (src_is_dir and any(True for _ in
                                              _iter_symlinks(src_abs))):
            _check_symlink_privilege()

    if not dry_run:
        if preserve_symlinks and src_is_link:
            # Recreate the link instead of following it (copy2 follows
            # symlinks and would copy the target's content).
            real_dst = (dst if not os.path.isdir(dst)
                        else os.path.join(dst, os.path.basename(src)))
            os.symlink(os.readlink(src), real_dst,
                       target_is_directory=os.path.isdir(src))
        elif src_is_dir:
            # symlinks=True is only passed when the flag is on, keeping
            # the default-off call identical to the original one.
            copytree_kwargs = {'symlinks': True} if preserve_symlinks else {}
            if copy_function is None:
                shutil.copytree(src, dst, **copytree_kwargs)
            else:
                shutil.copytree(src, dst, copy_function=copy_function,
                                **copytree_kwargs)
        else:
            if copy_function is None:
                shutil.copy2(src, dst)
            else:
                copy_function(src, dst)

    if (preserve_symlinks and retarget_symlinks and src_is_dir
            and not src_is_link):
        _retarget_symlinks(src, dst, dry_run, printer)

    printer.print_general_run_log(f"Copied {src} to {dst}")


def merge_folders(src: str | Path,
                  dst: str | Path,
                  dry_run: bool = False,
                  run_log: bool = False) -> dict[str, int]:
    """
    Merge all files from ``src`` into ``dst`` without ever overwriting.

    For each source file, matched against ``dst`` by relative path:
    * Destination does not exist: the file is copied (missing parent
      directories are created automatically).
    * Destination exists and both are files with identical content
      (SHA-256): the file is skipped.
    * Destination exists and both are files with different content: the
      source file is copied under an auto-renamed name
      (``stem_0.ext``, ``stem_1.ext``, ...).
    * Destination exists but is not a file (e.g. a directory): the source
      file is copied under an auto-renamed name.

    Files that exist only in ``dst`` are left untouched, and empty
    directories in ``src`` are not created in ``dst``. Hashes are computed
    in ``dry_run`` mode as well, so the returned statistics are accurate
    for a preview.

    Parameters
    ----------
    src : str | Path
        Source folder to merge from.
    dst : str | Path
        Target folder to merge into. Existing files are never overwritten.
    dry_run : bool, default False
        If True, only preview the actions without touching the filesystem.
    run_log : bool, default False
        If True, print a log line for every action. In dry_run mode,
        preview lines are printed instead.

    Returns
    -------
    dict of str to int
        Statistics with keys ``copied``, ``skipped``, ``renamed``.

    Raises
    ------
    FileNotFoundError
        If ``src`` or ``dst`` does not exist.
    ValueError
        If ``src`` or ``dst`` is not a directory, or if they are the same
        folder, or if ``dst`` is nested inside ``src``.
    """
    MAX_TRY = 10000  # max tries to find a free rename suffix

    printer = Printer(dry_run=dry_run, run_log=run_log, ignore_warning=False)

    src_path = Path(src)
    dst_path = Path(dst)
    _validate(src_path, dst_path)

    copied = skipped = renamed = 0

    src_files = ls(directory=str(src_path), recursive=True, path_type='rel_path')

    for rel_str in src_files:
        rel = Path(rel_str).as_posix()  # normalize separators for printing
        src_file = src_path / rel_str
        dst_file = dst_path / rel_str

        if not dst_file.exists():
            printer.print_general_run_log(f"[COPY] {rel}")
            if not dry_run:
                copy(str(src_file), str(dst_file), make_dir=True)
            copied += 1
        elif not dst_file.is_file():
            new_dst = Path(get_unique_new_dst(str(dst_file), MAX_TRY))
            printer.print_general_run_log(
                f"[RENAME] {rel} -> {new_dst.relative_to(dst_path).as_posix()} "
                f"(destination is not a file)")
            if not dry_run:
                copy(str(src_file), str(new_dst), make_dir=True)
            renamed += 1
        elif is_same_file(src_file, dst_file):
            printer.print_general_run_log(f"[SKIP] {rel} (same SHA-256)")
            skipped += 1
        else:
            new_dst = Path(get_unique_new_dst(str(dst_file), MAX_TRY))
            printer.print_general_run_log(
                f"[RENAME] {rel} -> {new_dst.relative_to(dst_path).as_posix()} "
                f"(different SHA-256)")
            if not dry_run:
                copy(str(src_file), str(new_dst), make_dir=True)
            renamed += 1

    return {"copied": copied, "skipped": skipped, "renamed": renamed}


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
    """Generate a non-existing path by appending a numeric suffix.

    Candidates are ``stem_0.ext``, ``stem_1.ext``, ...; returns the first
    one that does not exist (str with forward slashes). Raises RuntimeError
    if no free name is found within ``MAX_TRY`` tries.
    """
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


def _validate(src_path: Path, dst_path: Path) -> None:
    """Validate merge inputs; raise FileNotFoundError / ValueError."""
    if not src_path.exists():
        raise FileNotFoundError(f"Source folder not found: {src_path}")
    if not dst_path.exists():
        raise FileNotFoundError(f"Destination folder not found: {dst_path}")
    if not src_path.is_dir():
        raise ValueError(f"Not a directory: {src_path}")
    if not dst_path.is_dir():
        raise ValueError(f"Not a directory: {dst_path}")
    if is_same_path(src_path, dst_path):
        raise ValueError("Source and destination must be different folders.")
    if src_path.resolve() in dst_path.resolve().parents:
        raise ValueError(
            f"Destination folder must not be inside the source folder: {dst_path}")


def _map_link_target(link_target, src_root, dst_root):
    """Remap an absolute symlink target inside ``src_root`` to the
    corresponding location under ``dst_root``; return the target
    unchanged otherwise (relative, outside ``src_root``, or cross-drive).

    The Windows ``\\\\?\\`` long-path prefix is preserved through the
    mapping. Pure string math only — never touches the filesystem and
    never resolves links, so ``src_root`` may no longer exist (after a
    move).

    Parameters
    ----------
    link_target : str
        Stored target string as returned by ``os.readlink``.
    src_root : str
        Absolute, normalized source root.
    dst_root : str
        Absolute destination root.

    Returns
    -------
    str
        The remapped target, or the original string verbatim.
    """
    prefix = "\\\\?\\"
    has_prefix = link_target.startswith(prefix)
    clean_target = link_target.removeprefix(prefix)
    clean_src = str(src_root).removeprefix(prefix)
    try:
        common = os.path.commonpath([clean_target, clean_src])
        if os.path.isabs(clean_target) and \
                os.path.normpath(common) == os.path.normpath(clean_src):
            rel_part = os.path.relpath(clean_target, clean_src)
            new_target = str(Path(dst_root) / rel_part)
            return f"{prefix}{new_target}" if has_prefix else new_target
    except ValueError:
        # different drives (C:\ vs D:\) → commonpath raises
        pass
    return link_target


def _check_symlink_privilege():
    """Raise PermissionError if symlinks cannot be created here.

    Probes with a throwaway symlink in a temporary directory, so a
    missing right is detected before any part of a copy/move has run
    (also in dry_run mode, where it serves as a feasibility check).
    """
    with tempfile.TemporaryDirectory() as tmp:
        try:
            os.symlink(os.path.join(tmp, 'probe_target'),
                       os.path.join(tmp, 'probe_link'))
        except OSError as exc:
            raise PermissionError(
                'Creating symlinks is not permitted in this environment '
                '(Windows needs admin rights or Developer Mode); the '
                'requested operation would create or rewrite symlinks.'
            ) from exc


def _iter_symlinks(walk_root):
    """Yield the paths of all symlinks under ``walk_root``.

    os.walk is used directly instead of ``scanner.ls`` because ``ls()``
    yields files only and cannot see symlinked directories (which
    appear under ``dirs``).
    """
    if not os.path.isdir(walk_root):
        return
    for root, dirs, files in os.walk(walk_root, followlinks=False):
        for name in dirs + files:
            path = os.path.join(root, name)
            if os.path.islink(path):
                yield path


def _iter_retargets(walk_root, src_root, dst_root):
    """Yield ``(path, old_target, new_target)`` for every symlink under
    ``walk_root`` whose remapped target differs from the stored one."""
    for path in _iter_symlinks(walk_root):
        old_target = os.readlink(path)
        new_target = _map_link_target(old_target, src_root, dst_root)
        if new_target != old_target:
            yield path, old_target, new_target


def _retarget_symlinks(src_root, dst_root, dry_run, printer: Printer):
    """Rewrite symlinks whose absolute targets pointed inside
    ``src_root`` so they point inside ``dst_root``.

    Real mode walks ``dst_root`` (the copied/moved tree) and rewrites
    matching links. Dry-run mode walks ``src_root`` (which still
    exists) and only previews the same rewrites.
    """
    src_abs = os.path.abspath(src_root)
    dst_abs = os.path.abspath(dst_root)
    walk_root = src_abs if dry_run else dst_abs

    for path, old_target, new_target in _iter_retargets(walk_root, src_abs,
                                                        dst_abs):
        printer.print_general_run_log(
            f"[RETARGET] {path}: {old_target} -> {new_target}")
        if not dry_run:
            os.unlink(path)
            os.symlink(new_target, path)
