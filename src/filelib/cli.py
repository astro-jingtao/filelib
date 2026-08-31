"""Command-line interface for filelib.

Thin argparse adapter over ``filelib.operator`` and
``filelib.identifier``; installed as the ``filelib`` console script.
Output conventions (``[dry-run] `` prefixes, run-log lines,
``Warning: `` lines, ``[RETARGET]`` / ``[COPY]`` / ``[SKIP]`` /
``[RENAME]`` traces) come from the library's ``Printer``.

Exit codes: 0 success, 1 runtime error (or corrupted files found by
check-image), 2 usage error (argparse).
"""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version

import puremagic

from filelib.identifier import is_file_corrupted
from filelib.operator import copy, merge_folders, move

_EXIT_CODES_EPILOG = """\
exit codes:
  0  success (check-image: no corrupted files and no per-file errors)
  1  runtime error, or check-image found corrupted files / per-file errors
  2  usage error
"""


def _get_version() -> str:
    try:
        return version('filelib')
    except PackageNotFoundError:
        return 'unknown (not installed as a distribution)'


def _add_common_flags(sub: argparse.ArgumentParser) -> None:
    sub.add_argument('--dry-run', action='store_true', dest='dry_run',
                     help='preview only; print the actions without '
                          'touching the filesystem')
    sub.add_argument('--run-log', action=argparse.BooleanOptionalAction,
                     default=True, dest='run_log',
                     help='print one log line per action (default: on; '
                          'disable with --no-run-log)')


def _add_rename_flags(sub: argparse.ArgumentParser) -> None:
    sub.add_argument('--rename-format', dest='rename_format',
                     default='{stem}_{i}{suffix}', metavar='FMT',
                     help="auto-rename template applied to the destination "
                          "file name; placeholders {stem}, {suffix}, {i} "
                          "(format specs such as {i:03d} supported; "
                          "default: '%(default)s')")
    sub.add_argument('--rename-start', dest='rename_start', type=int,
                     default=0, metavar='N',
                     help='first candidate index for auto-renames; use 1 '
                          'for Windows-style name_1.ext (default: %(default)s)')


def cmd_copy(args: argparse.Namespace) -> int:
    # --retarget-symlinks implies --preserve-symlinks: the library would
    # otherwise warn and silently disable retargeting (a hidden no-op for
    # a user who explicitly asked for retargeting).
    copy(args.src, args.dst,
         dry_run=args.dry_run,
         exist_policy=args.exist_policy,
         make_dir=args.make_dir,
         run_log=args.run_log,
         preserve_symlinks=args.preserve_symlinks or args.retarget_symlinks,
         retarget_symlinks=args.retarget_symlinks,
         rename_format=args.rename_format,
         rename_start=args.rename_start)
    return 0


def cmd_move(args: argparse.Namespace) -> int:
    move(args.src, args.dst,
         dry_run=args.dry_run,
         exist_policy=args.exist_policy,
         make_dir=args.make_dir,
         run_log=args.run_log,
         retarget_symlinks=args.retarget_symlinks,
         rename_format=args.rename_format,
         rename_start=args.rename_start)
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    stats = merge_folders(args.src, args.dst,
                          dry_run=args.dry_run,
                          run_log=args.run_log,
                          rename_format=args.rename_format,
                          rename_start=args.rename_start)
    print(f"Summary: {stats['copied']} copied, {stats['skipped']} skipped, "
          f"{stats['renamed']} renamed")
    return 0


def cmd_check_image(args: argparse.Namespace) -> int:
    ok = corrupted = unsupported = errors = 0
    for path in args.files:
        try:
            result = is_file_corrupted(path, mime_method=args.mime_method)
        except (OSError, ValueError, puremagic.PureError) as exc:
            # Per-file errors are reported with the path and the batch
            # continues: OSError = missing/unreadable file; puremagic
            # raises PureError (a LookupError, not covered by main's
            # central handler) for unidentifiable content and a plain
            # ValueError for empty input. Invalid mime_method is
            # impossible here (argparse choices).
            print(f"Error: {path}: {exc}", file=sys.stderr)
            errors += 1
            continue
        if result is None:
            print(f"{path}: unsupported")
            unsupported += 1
        elif result:
            print(f"{path}: corrupted")
            corrupted += 1
        else:
            print(f"{path}: ok")
            ok += 1
    print(f"Summary: {len(args.files)} files: {ok} ok, {corrupted} corrupted, "
          f"{unsupported} unsupported, {errors} errors")
    return 1 if (corrupted or errors) else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='filelib',
        description='File utilities: copy/move with conflict policies and '
                    'symlink retargeting, non-overwriting folder merge, '
                    'image corruption checks.',
        epilog=_EXIT_CODES_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {_get_version()}')
    sub = parser.add_subparsers(dest='command', required=True,
                                metavar='COMMAND')

    p_copy = sub.add_parser(
        'copy',
        help='copy a file or directory (symlinks are followed by default)')
    p_copy.add_argument('src', help='source file, directory, or symlink')
    p_copy.add_argument('dst',
                        help='destination path (existing dir: copied into '
                             'it as dst/<basename(src)>)')
    p_copy.add_argument('--exist-policy', dest='exist_policy',
                        choices=['default', 'overwrite', 'rename'],
                        default='default',
                        help='what to do when dst exists as a file '
                             '(default: %(default)s)')
    p_copy.add_argument('--make-dir', action='store_true', dest='make_dir',
                        help='create missing parent directories of dst')
    p_copy.add_argument('--preserve-symlinks', action='store_true',
                        dest='preserve_symlinks',
                        help='copy symlinks as links instead of following '
                             'them')
    p_copy.add_argument('--retarget-symlinks', action='store_true',
                        dest='retarget_symlinks',
                        help='rewrite absolute in-tree link targets in the '
                             'copy (implies --preserve-symlinks)')
    _add_common_flags(p_copy)
    _add_rename_flags(p_copy)
    p_copy.set_defaults(func=cmd_copy)

    p_move = sub.add_parser(
        'move',
        help='move a file or directory (symlinks always move as links)')
    p_move.add_argument('src', help='source file, directory, or symlink')
    p_move.add_argument('dst',
                        help='destination path (existing dir: moved into '
                             'it as dst/<basename(src)>)')
    p_move.add_argument('--exist-policy', dest='exist_policy',
                        choices=['default', 'overwrite', 'rename'],
                        default='default',
                        help='what to do when dst exists as a file '
                             '(default: %(default)s)')
    p_move.add_argument('--make-dir', action='store_true', dest='make_dir',
                        help='create missing parent directories of dst')
    p_move.add_argument('--retarget-symlinks', action='store_true',
                        dest='retarget_symlinks',
                        help='after the move, rewrite absolute in-tree '
                             'link targets that would dangle')
    _add_common_flags(p_move)
    _add_rename_flags(p_move)
    p_move.set_defaults(func=cmd_move)

    p_merge = sub.add_parser(
        'merge',
        help='merge src folder into dst folder; never overwrites '
             '(SHA-256 dedupe, auto-rename on conflict)')
    p_merge.add_argument('src', help='source folder')
    p_merge.add_argument('dst',
                         help='target folder (existing files are kept)')
    _add_common_flags(p_merge)
    _add_rename_flags(p_merge)
    p_merge.set_defaults(func=cmd_merge)

    p_chk = sub.add_parser(
        'check-image',
        help='check image files (jpeg/png/gif/bmp/webp) for '
             'truncation/corruption')
    p_chk.add_argument('files', nargs='+', metavar='FILE',
                       help='image files to check')
    p_chk.add_argument('--mime-method', dest='mime_method',
                       choices=['magic', 'extension'], default='magic',
                       help='MIME detection from file content or file name '
                            'suffix (default: %(default)s)')
    p_chk.set_defaults(func=cmd_check_image)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)  # usage errors exit 2 here
    try:
        return args.func(args)
    except (OSError, ValueError, RuntimeError) as exc:
        # Expected library errors surface as one visible line; anything
        # else propagates as a traceback (a bug must not be masked).
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
