# filelib

`filelib` is a lightweight Python utility library for common file workflows, including:
- directory scanning and filtering
- file/folder copy, move, and remove operations
- path resolution and file comparison checks
- HTTP file downloads
- basic image corruption checks

The package is designed for script reuse across projects and supports safe operation patterns like `dry_run` and run-time logging.

## Requirements

- Python `>= 3.9`

## Installation

Install from the project root in editable mode:

```bash
pip install -e .
```

## Package Structure

- `filelib.scanner`
  - `ls`: list files with filter, recursion, and path formatting options
  - `is_empty_dir`: check whether a directory is empty (shallow by default; `recursive=True` treats directories holding only empty subdirectories as empty)
- `filelib.operator`
  - `remove`: delete file/folder with `recursive` control
  - `move`: move path with destination conflict policies; `retarget_symlinks` retargets in-tree absolute links after a move
  - `copy`: copy file/folder with destination conflict policies; `preserve_symlinks` keeps symlinks as links, `retarget_symlinks` rewrites in-tree absolute targets in the copy
  - `merge_folders`: one-way merge `src` into `dst` without overwriting (SHA-256 dedupe, auto-rename on conflict)
  - `dry_run_session`: context manager sharing virtual created-directory state across a batch of dry-run `copy`/`move` calls
- `filelib.resolver`
  - `is_same_path`: compare two paths after `Path.resolve()` normalization
- `filelib.checker`
  - `is_same_file`: check if two files are identical (hash or byte-level comparison)
  - `is_same_folder`: check if two folders contain identical files
- `filelib.downloader`
  - `download_response`: download URL content to a file path
- `filelib.identifier`
  - `get_mime_magic`: MIME detection by file signature
  - `get_mime_extension`: MIME detection by extension
  - `is_file_corrupted`: image completeness check for common formats
- `filelib.cli`
  - `main`: console entry point `filelib` with `copy` / `move` / `merge` / `check-image` subcommands mirroring `operator` and `identifier` (see [Command Line Interface](#command-line-interface))
- `filelib.printer`
  - internal helper used for `dry_run`, run logs, and warning messages
- `filelib.skills`
  - the agent-facing usage skill shipped as package data (`filelib/skills/filelib/skill/SKILL.md`, deployment guide `filelib/skills/SKILL-DEPLOY.md`); `python -m filelib.skills` prints the installed skills root

## Quick Start

### 1) Scan files in a directory

```python
from filelib.scanner import ls

files = ls(
    directory="data/images",
    match_func=lambda f: f.lower().endswith((".jpg", ".jpeg", ".png")),
    recursive=True,
    path_type="abs_full_path",
    follow_symlinks=True,
)

print(files)
```

### 2) Safe move flow with preview

```python
from filelib.operator import move

# Preview first (no filesystem change)
move(
    src="input/a.txt",
    dst="output/a.txt",
    dry_run=True,
    run_log=True,
    exist_policy="rename",
    make_dir=True,
)

# Execute
move(
    src="input/a.txt",
    dst="output/a.txt",
    dry_run=False,
    run_log=True,
    exist_policy="rename",
    make_dir=True,
)
```

### 3) Remove files/folders

```python
from filelib.operator import remove

# Remove file
remove("tmp/a.txt")

# Remove non-empty directory recursively
remove("tmp/cache", recursive=True)

# Conservative mode: skip non-empty directories
remove("tmp/cache", recursive="skip", run_log=True)
```

### 4) Download a file

```python
from filelib.downloader import download_response

status = download_response(
    url="https://example.com/file.zip",
    filename="downloads/file.zip",
    force=False,
    verbose=True,
    timeout=30,
)

print(status)
```

### 5) Detect corrupted images

```python
from filelib.identifier import is_file_corrupted

result = is_file_corrupted(
    "data/images/example.jpg",
    mime_method="magic",
    unsupported_policy="return",
    unsupported_return=None,
)

print(result)  # True: corrupted, False: complete, None: unsupported mime (with policy=return)
```

### 6) Merge two folders without overwriting

```python
from filelib.operator import merge_folders

# Preview first (no filesystem change)
stats = merge_folders(src="backup/photos", dst="library/photos", dry_run=True)
print(stats)  # {'copied': 12, 'skipped': 5, 'renamed': 3}

# Execute with a per-file log
stats = merge_folders(src="backup/photos", dst="library/photos", run_log=True)
print(stats)

# Windows-style conflict names: photo (1).jpg, photo (2).jpg, ...
stats = merge_folders(
    src="backup/photos", dst="library/photos", rename_format="{stem} ({i}){suffix}", rename_start=1
)
```

### 7) Copy/move a folder while preserving symbolic links

```python
from filelib.operator import copy, move

# Preview first: prints [dry-run] [RETARGET] lines for links that will be
# rewritten (also raises PermissionError here if links could not be created)
copy(src="game/mod", dst="backup/mod", preserve_symlinks=True, retarget_symlinks=True, dry_run=True)

# Copy: symlinks are recreated as symlinks; links whose absolute targets
# point inside "game/mod" are retargeted to point inside "backup/mod"
copy(src="game/mod", dst="backup/mod", preserve_symlinks=True, retarget_symlinks=True, run_log=True)

# Move: links are always preserved by the move itself; retarget_symlinks
# additionally fixes absolute in-tree links, which would otherwise dangle
move(src="game/mod", dst="backup/mod", retarget_symlinks=True, run_log=True)
```

## Command Line Interface

Installing the package registers the `filelib` console script (also available without reinstalling as `python -m filelib.cli`). It is a thin adapter over the Python API — same flags, same output conventions (`[dry-run]` previews, run-log lines, `[RETARGET]` / `[COPY]` / `[SKIP]` / `[RENAME]` traces):

```powershell
filelib copy SRC DST [--exist-policy {default,overwrite,rename}] [--make-dir]
           [--preserve-symlinks] [--retarget-symlinks] [--dry-run]
           [--run-log | --no-run-log] [--rename-format FMT] [--rename-start N]
filelib move SRC DST [--exist-policy ...] [--make-dir] [--retarget-symlinks]
           [--dry-run] [--run-log | --no-run-log] [--rename-format FMT] [--rename-start N]
filelib merge SRC DST [--dry-run] [--run-log | --no-run-log]
            [--rename-format FMT] [--rename-start N]
filelib check-image FILE [FILE ...] [--mime-method {magic,extension}]
```

Preview-then-execute flow (recommended for anything destructive):

```powershell
# 1. Preview: prints [dry-run] lines, touches nothing
filelib copy game/mod backup/mod --retarget-symlinks --dry-run

# 2. Execute: symlinks are kept as links and in-tree absolute targets are
#    rewritten to point into the copy (--retarget-symlinks implies
#    --preserve-symlinks, unlike the Python API which warns and disables)
filelib copy game/mod backup/mod --retarget-symlinks

# Windows-style conflict names: report_1.txt, report_2.txt, ...
filelib copy report.txt archive\report.txt --exist-policy rename --rename-start 1

# Create missing parent directories of the destination
filelib move incoming\data.txt sorted\2026\data.txt --make-dir

# Folder merge: never overwrites; dry-run prints exact statistics
filelib merge backup\photos library\photos --dry-run
filelib merge backup\photos library\photos

# Batch image check in a pipeline
filelib check-image (Get-ChildItem -Recurse -Filter *.png).FullName
if ($LASTEXITCODE -eq 1) { Write-Host "corrupted images found" }
```

Notes:

- The run log is **on by default** in the CLI (`--no-run-log` to silence); this is the only default that differs from the Python API.
- Exit codes: `0` success (`check-image`: no corrupted files and no per-file errors); `1` runtime error or corrupted files found; `2` usage error.
- `check-image` prints one `<path>: ok|corrupted|unsupported` line per file plus a `Summary:` line. Unsupported MIME types (anything beyond jpeg/png/gif/bmp/webp) do **not** affect the exit code. Per-file errors (missing file; content that cannot be identified with `--mime-method magic`, e.g. an empty or non-image file) are reported on stderr as `Error: <path>: <message>` and the remaining files are still checked; any such error makes the exit code `1`.
- PowerShell does not expand wildcards for native commands — pass a list as in the example above, and single-quote templates like `'{stem}_{i}{suffix}'` so braces stay literal.

## API Notes and Behaviors

### `scanner.ls`

- `path_type` supports (default `abs_full_path`):
  - `file_only`
  - `raw_full_path`
  - `abs_full_path`
  - `rel_path`
- `follow_symlinks` controls whether recursive scan follows directory symlinks.
  - default: `True`
  - set `False` to skip traversing symlinked directories
- If `path_type="file_only"`, duplicate filenames from different folders may collide.
- Use `on_duplicates` in `file_only` mode:
  - `raise`
  - `warn`
  - `ignore`
- Any other `on_duplicates` value raises `ValueError` before scanning starts.
- Any other `path_type` value raises `ValueError` before scanning starts (an empty directory does not skip the check).

### `scanner.is_empty_dir`

- `recursive` behavior:
  - `False` (default): the directory is empty only when it contains no entries at all — files, subdirectories, and hidden entries such as `.gitkeep` all count as content
  - `True`: the directory is empty when it contains no files at any depth, i.e. a directory holding only empty subdirectories (arbitrarily nested) counts as empty; directory symlinks are followed (same default as `ls()`)
- Raises `FileNotFoundError` if the path does not exist, and `NotADirectoryError` if it exists but is not a directory.

### `operator.remove`

- `recursive` behavior:
  - `True`: remove directory and all contents
  - `False`: fail on non-empty directory
  - `"skip"`: skip non-empty directory
- Any other `recursive` value raises `ValueError` before anything is removed.
- `dry_run=True` prints intended actions without changing filesystem.

### `operator.move` and `operator.copy`

- `exist_policy`:
  - `default`: keep default behavior
  - `overwrite`: remove existing destination file first
  - `rename`: auto-generate destination suffix (`_0`, `_1`, ...; pattern configurable via `rename_format`/`rename_start`)
- `rename_format` (default `'{stem}_{i}{suffix}'`): template for the auto-renamed destination used by `exist_policy="rename"`, applied to the destination **file name** (candidates stay in the directory of `dst`). Placeholders: `{stem}` (file name without its final suffix), `{suffix}` (final suffix with its leading dot, empty for names like `README`), `{i}` (candidate index, format specs supported, e.g. `{i:03d}` for zero padding; literal braces as `{{`/`}}`).
- `rename_start` (default `0`): first candidate index; use `1` for Windows-style `name_1.ext` numbering.
- An invalid `exist_policy`, an invalid template (unknown placeholders, no placeholder varying with the index) or a negative `rename_start` raises `ValueError` up front — whatever the destination state is, also in `dry_run` mode; a non-`str` `rename_format` or non-`int` `rename_start` raises `TypeError` instead.
- `make_dir=True` creates missing destination parent directories.
- In a batch of dry-run calls with `make_dir=True`, every call re-reports `Create directory <dir>` for a directory the batch would already have created; wrap the batch in `operator.dry_run_session()` to report each directory once, like the real run (see [`operator.dry_run_session`](#operatordry_run_session)).
- `exist_policy` applies only when `dst` exists as a **file**; when `dst` is missing or an existing directory it is ignored (file/directory `src` is then placed into `dst/<basename(src)>`, or `copytree` raises `FileExistsError` for a directory `src` onto an existing directory).
- `preserve_symlinks` (`copy` only, default `False`): symlinks are kept as links instead of followed — a symlink `src` is recreated at `dst` with its original target, and links inside a copied directory tree are recreated as links (original targets unchanged).
- `retarget_symlinks` (`copy` and `move`, default `False`): with a real-directory `src`, links whose absolute targets lie inside `src` are rewritten to the corresponding location under `dst` after the copy/move. Relative links and links pointing outside the tree are kept verbatim. Single symlinks are never retargeted — only the link itself is copied/moved while its target stays valid where it is; retargeting is only sound when the whole tree containing both the link and its target is transported.
  - On `copy` it requires `preserve_symlinks=True`; otherwise a warning is printed and nothing is retargeted.
  - On `move` links are preserved by `shutil.move` itself regardless of the flag; the flag only adds retargeting (fixing links that would dangle after the move).
- Privilege pre-check: if the operation would create or rewrite at least one link, symlink-creation rights are probed **before any filesystem change**; a missing right raises `PermissionError` — in `dry_run` mode too, so previews double as feasibility checks.
- `dry_run=True` previews each rewrite as `[RETARGET] <link>: <old> -> <new>`.

### `operator.dry_run_session`

- Context manager: dry-run `copy`/`move` calls inside share one virtual view of created directories.
- Problem it solves: a dry-run call does not create directories, so in a batch of dry-run calls into the same missing parent, every call prints `Create directory <dir>` again — while the corresponding real run prints it only for the first call.
- Inside the session a dry-run call remembers the directories it would have created — including every missing ancestor, mirroring `os.makedirs` — and later calls treat them as existing: `Create directory` is printed once per directory, and a `make_dir=False` call into a virtually created directory no longer raises `FileNotFoundError`.
- Real runs never consult the session (the real filesystem is the truth), and only directory creation is tracked — destination *file* existence (auto-rename candidate checks included) still comes from the real filesystem.

```python
from filelib.operator import copy, dry_run_session

with dry_run_session():
    for name in files:
        copy(name, f"out/sub/{name}", dry_run=True, make_dir=True, run_log=True)
# "Create directory out/sub" appears once, not once per file
```

### `operator.merge_folders`

- Never overwrites: on name conflict the destination file is kept, and the source file is copied under an auto-renamed name.
- Rename format defaults to `stem_0.ext`, `stem_1.ext`, ... and is configurable via `rename_format` / `rename_start` (same template semantics as `operator.move/copy` with `exist_policy="rename"`; an invalid template raises `ValueError` and wrong argument types raise `TypeError`, both before any file is copied).
- Files are matched by relative path:
  - destination missing -> direct copy with parent directories created
  - identical SHA-256 -> skipped
  - different content or non-file destination (e.g. a directory) -> renamed copy
- Empty directories in `src` are not created in `dst`; extra files in `dst` are left untouched.
- `dry_run=True` still hashes conflicting files, so the returned statistics are accurate for the preview.
- Returns `{"copied": n, "skipped": n, "renamed": n}`.
- Raises `FileNotFoundError` if `src`/`dst` is missing; `ValueError` if a path is not a directory, or `src` and `dst` are the same folder, or `dst` is nested inside `src`.

### `checker.is_same_file` / `checker.is_same_folder`

- `is_same_file`: `mode='hash'` (SHA-256, default) or `'full'` (byte-by-byte); raises `FileNotFoundError` for a missing file and `ValueError` for an invalid mode.
- `is_same_folder`: recursive, files matched by relative path; `file_selector_func` filters which files count, `file_compare_mode` picks the underlying `is_same_file` mode (an invalid value raises `ValueError` before scanning starts, even when `compare_func` overrides the mode), `compare_func` overrides the per-file comparison entirely, `report=True` prints the differences. Two folders whose (selected) file sets are both empty are identical.

### `identifier.is_file_corrupted`

- Supports MIME checks for:
  - `image/jpeg`
  - `image/png`
  - `image/gif`
  - `image/bmp`
  - `image/webp`
- MIME source can be:
  - `magic` (content-based)
  - `extension` (suffix-based)
- An invalid `mime_method` or `unsupported_policy` value raises `ValueError` up front, before the file is opened — even when an explicit `mime=` or a supported MIME type would have made the value unused.

## Testing

The project includes tests under `tests/`.

Run tests with:

```bash
pytest -q
```

Network-bound downloader checks live in `tests/test_downloader_live.py` and are skipped by default; set `FILELIB_LIVE_TESTS=1` to run them against a real remote endpoint.

## Current Limitations

- `download_response` does not create parent directories automatically.
- `merge_folders` follows directory symlinks while scanning; symlink cycles are not detected and can cause duplicated traversal or statistics.
- `move` preserves symlinks inherently (`shutil.move` behavior); `retarget_symlinks=True` only adds the in-tree retargeting pass.
- With `preserve_symlinks=True` and `exist_policy="default"`, copying a single symlink onto an existing file raises `FileExistsError` instead of silently overwriting (plain `copy2` would overwrite).
- Absolute links pointing outside the source tree are kept verbatim by the symlink flags and may dangle after a move.
- An existing destination that is a symlink is not handled by `exist_policy` (it only distinguishes file vs directory).

## License

This project is licensed under the GNU General Public License v3.0 only (GPL-3.0-only); see [LICENSE](LICENSE) for the full text.
