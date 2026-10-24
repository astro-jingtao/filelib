---
name: filelib
description: Drive the filelib Python package — directory scanning and filtering, copy, move, remove, non-overwriting folder merge, path and content comparison, HTTP downloads, and image corruption checks — from Python or the `filelib` CLI. Use when a task must scan or filter files, reorganize or clean up files and folders, merge folders without overwriting anything, verify two files or folder trees are identical, check whether two paths point to the same location, download a URL to disk, or find truncated or corrupted jpeg, png, gif, bmp, webp images.
---

# File Work with filelib

## Role

You are an agent operating on files through one toolkit. Reads go through `scanner`, `checker`, and `resolver`; every filesystem change goes through `operator` (or the `filelib` CLI that mirrors it), previewed before the real run. Your job is to:

1. Pick the narrowest API for the task.
2. Preview mutations with `dry_run=True` and decide conflict behavior explicitly.
3. Execute with `run_log=True`, then verify the result.

Working progression:

```text
pick API → dry-run preview → execute with run log → verify
```

---

# Hard Rules

## R1 — Preview before you mutate

Every `copy` / `move` / `remove` / `merge_folders` run runs once with `dry_run=True` before running for real. A preview is a feasibility check, not just a printout: rename-template validation and the symlink-privilege probe raise in `dry_run` too, so an impossible operation fails before anything changes.

## R2 — Decide conflicts explicitly, never by default

`exist_policy` guards exactly one case — `dst` exists as a **file** — and its `'default'` outcome there is destructive: `copy` silently overwrites, `move` replaces. When a collision is possible, choose `'rename'` or a deliberate `'overwrite'`; likewise pick `remove`'s `recursive` mode (`True` / `False` / `'skip'`) consciously whenever a directory is involved.

## R3 — Verify, and let errors be loud

After executing, confirm the outcome (`ls()`, `Path.exists()`, or the statistics returned by `merge_folders`). filelib raises instead of guessing — bad enum values, missing parents, occupied destinations; read the message through Failure Shapes below instead of wrapping or retrying blindly.

---

# The Toolkit

| Task | Call |
| ---- | ---- |
| List / filter files | `scanner.ls(directory, match_func=None, recursive=False, path_type='abs_full_path', on_duplicates='raise', follow_symlinks=True)` |
| Is a directory empty? | `scanner.is_empty_dir(directory, recursive=False)` |
| Copy / move | `operator.copy(...)` / `operator.move(...)` — `exist_policy`, `make_dir`, symlink flags, `rename_format` |
| Batch dry-run preview | wrap the batch in `with operator.dry_run_session():` — directories that would have been created are reported once |
| Delete | `operator.remove(path, recursive=False)` |
| Merge folders, never overwrite | `operator.merge_folders(src, dst)` → `{'copied', 'skipped', 'renamed'}` |
| Same location? | `resolver.is_same_path(path1, path2)` |
| Identical files? | `checker.is_same_file(file1, file2, mode='hash')` |
| Identical trees? | `checker.is_same_folder(folder1, folder2, ...)` |
| MIME / image integrity | `identifier.get_mime_magic` / `get_mime_extension` / `is_file_corrupted` |
| Download | `downloader.download_response(url, filename, force=False)` |
| Shell access | `filelib copy / move / merge / check-image` (console script, or `python -m filelib.cli`) |

---

# Behavior That Decides Outcomes

## Scanning — `scanner.ls`

- Returns a **sorted** list; `match_func` receives the file **name**, not its path.
- `recursive=False` (default) lists only the top directory's files.
- `path_type` picks the returned format: `abs_full_path` (the actual default), `rel_path`, `raw_full_path`, `file_only`.
- `file_only` can collide across subdirectories → `on_duplicates` `raise` / `warn` / `ignore`; any other value raises `ValueError` up front.
- `follow_symlinks=True` (default) matters only when recursing into symlinked directories.

## Empty directories — `scanner.is_empty_dir`

- Shallow (default): empty means no entries at all — a lone `.gitkeep` counts as content.
- `recursive=True`: empty means no files at any depth; a tree of only empty subdirectories counts as empty (directory symlinks followed).
- Raises `FileNotFoundError` (missing path) / `NotADirectoryError`.

## Destinations — `operator.copy` / `operator.move`

What happens depends on what `dst` is; `exist_policy` applies only to the last row:

| `dst` state | Behavior |
| ----------- | -------- |
| missing | plain copy/move; `make_dir=True` creates missing parents, otherwise `FileNotFoundError` |
| existing **directory** | source lands **inside** as `dst/<basename(src)>` |
| existing **file** | `'default'` — `copy` silently overwrites, `move` replaces; `'overwrite'` — dst removed first; `'rename'` — first free name from `rename_format` |

- An invalid `exist_policy` string raises only when the policy actually fires (existing-file `dst`).
- Dry-run batches: a dry-run call never creates directories, so repeated calls into the same missing parent re-print `Create directory`. Wrap the batch in `with operator.dry_run_session():` and each directory is reported once, matching the real run (missing ancestors remembered like `os.makedirs`; destination *file* existence still comes from the real filesystem, and real runs ignore the session).
- `rename_format` (default `'{stem}_{i}{suffix}'`) renders the destination **file name**; placeholders `{stem}`, `{suffix}` (may be empty), `{i}` (format specs such as `{i:03d}` allowed). The template must vary with the index — value violations raise `ValueError` when a rename fires (in `dry_run` too), wrong argument types raise `TypeError`; `merge_folders` validates the spec up front instead.
- Copying follows symlinks by default; a dangling link inside a tree raises.

## Deletion — `operator.remove`

- Missing path: warning + skip, no exception.
- File: removed regardless of `recursive`.
- Directory: `recursive=True` → remove everything; `False` → empty-only (`OSError` when non-empty); `'skip'` → non-empty directories skipped, empty ones still removed.

## Symlinks in copy/move

- `preserve_symlinks=True` (copy only): links are recreated as links with their original targets.
- `retarget_symlinks=True`: after transporting a real directory, absolute targets **inside** the tree are rewritten to the counterpart under `dst`; relative and outside-tree links stay verbatim; a single symlink is never retargeted. On `copy` it needs `preserve_symlinks=True` (otherwise warning + no retargeting); on `move` links travel as links anyway and the flag only adds retargeting.
- Creating or rewriting links requires symlink privilege (Windows: admin or Developer Mode). It is probed **before any filesystem change** — missing rights raise `PermissionError`, also in `dry_run`; the preview shows each rewrite as `[RETARGET] link: old -> new`.
- CLI: `filelib copy --retarget-symlinks` implies `--preserve-symlinks`.

## Merging — `operator.merge_folders`

Files are matched by relative path; nothing is ever overwritten:

| `dst` relative path | Outcome |
| ------------------- | ------- |
| missing | copied, missing parents created |
| same SHA-256 | skipped |
| different content, or `dst` not a file | copied under an auto-renamed name |

`dst`-only files are untouched; empty `src` directories are not created; `dry_run` still hashes, so the returned statistics are exact. Raises `FileNotFoundError` (missing folder) / `ValueError` (non-directory, same folder, `dst` inside `src`, invalid rename spec — the last before anything is copied).

## Comparison — `checker` / `resolver`

- `is_same_file`: `mode='hash'` (SHA256, default) or `'full'` (byte-by-byte).
- `is_same_folder`: recursive, files matched by relative path; `file_selector_func` filters which files count, `compare_func` overrides the per-file comparison, `report=True` prints the differences; two folders whose (selected) file sets are both empty are identical.
- `is_same_path`: both sides `Path.resolve()`d, then compared.

## Downloads — `downloader.download_response`

- Existing `filename` with `force=False`: skips and returns **`None`** — check for that, not only the status code.
- Otherwise returns the HTTP status; a non-200 status is returned, not raised.
- Never creates parent directories.

## Image integrity — `identifier.is_file_corrupted`

- MIME from content (`mime_method='magic'`, default) or from extension; an explicit `mime=` short-circuits detection. Supported: jpeg, png, gif, bmp, webp.
- Returns `True` (corrupted) / `False` (complete); unsupported MIME → `unsupported_return` (default `None`) with `unsupported_policy='return'`, or `ValueError` with `'raise'`.
- CLI `check-image`: one `<path>: ok|corrupted|unsupported` line per file plus a `Summary:` line; unsupported files do not affect the exit code; corrupted files and per-file errors (missing file, unidentifiable content) do → exit 1.

## CLI mirroring

`filelib copy / move / merge / check-image` maps one-to-one onto the Python API. One default differs: the run log is **on** (`--no-run-log` to silence). Exit codes 0 success / 1 runtime error or corrupted files found / 2 usage error.

---

# Recipes

### Scan, then act on the result

```python
from filelib.scanner import ls

stale = ls(
    directory="data",
    match_func=lambda n: n.endswith(".tmp"),
    recursive=True,
    path_type="abs_full_path",
)
```

### Move with preview, then execute

```python
from filelib.operator import move

move("a/source.txt", "b/target.txt", dry_run=True, exist_policy="rename", make_dir=True)
move("a/source.txt", "b/target.txt", run_log=True, exist_policy="rename", make_dir=True)
```

### Merge folders with Windows-style conflict names

```python
from filelib.operator import merge_folders

stats = merge_folders("incoming", "archive", dry_run=True)  # exact preview
stats = merge_folders(
    "incoming", "archive", run_log=True, rename_format="{stem} ({i}){suffix}", rename_start=1
)
```

### Transport a tree whose links must survive

```python
from filelib.operator import copy

copy(
    "game/mod", "backup/mod", preserve_symlinks=True, retarget_symlinks=True, dry_run=True
)  # previews [RETARGET] lines
copy("game/mod", "backup/mod", preserve_symlinks=True, retarget_symlinks=True, run_log=True)
```

### Audit a download batch for truncated images

```python
from filelib.scanner import ls
from filelib.identifier import is_file_corrupted

imgs = ls(
    "downloads",
    recursive=True,
    match_func=lambda n: n.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")),
)
bad = [
    p
    for p in imgs
    if is_file_corrupted(p, mime_method="magic", unsupported_policy="return") is True
]
```

From the shell: `filelib check-image <files...>` — exit code 1 when anything is corrupted.

---

# Failure Shapes

| Signal | Meaning | Response |
| ------ | ------- | -------- |
| `FileNotFoundError` about dst's parent | destination parent missing | pass `make_dir=True`, or create it first |
| `OSError: Directory not empty` | `remove(recursive=False)` on a non-empty directory | choose `recursive=True` or `'skip'` deliberately |
| `ValueError: exist_policy must be ...` | invalid policy, fired on an existing-file dst | use `default` / `overwrite` / `rename` |
| `ValueError: Invalid rename_format ...` | unknown placeholder, or template constant in `{i}` | keep `{i}` (or an index-dependent placeholder) in the template |
| `FileExistsError` | directory src onto existing dst (copytree); symlink recreated or moved onto an existing file | clear or rename the destination, or change policy |
| `shutil.Error` | source moved/copied into an occupied `dst/<basename(src)>` | rename or clear the occupant |
| `PermissionError` from the symlink probe | this environment cannot create links | enable Developer Mode / admin rights, or drop the symlink flags |
| `RuntimeError` after 10000 tries | no free auto-rename candidate | widen `rename_format` (e.g. `{i:03d}`) |
| `puremagic.PureError` (CLI) | content unidentifiable with `--mime-method magic` | pre-filter the file list, or use `--mime-method extension` |

---

# Limits

- `download_response` creates no parent directories; HTTP errors are returned, not raised.
- Recursive scans and `merge_folders` follow directory symlinks without cycle detection.
- `exist_policy` does not fire when `dst` is a symlink — only file vs directory is distinguished.
- Absolute links pointing outside a moved tree are kept verbatim and dangle afterwards.
