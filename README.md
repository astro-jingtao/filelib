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
- `filelib.operator`
  - `remove`: delete file/folder with `recursive` control
  - `move`: move path with destination conflict policies; `retarget_symlinks` retargets in-tree absolute links after a move
  - `copy`: copy file/folder with destination conflict policies; `preserve_symlinks` keeps symlinks as links, `retarget_symlinks` rewrites in-tree absolute targets in the copy
  - `merge_folders`: one-way merge `src` into `dst` without overwriting (SHA-256 dedupe, auto-rename on conflict)
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
- `filelib.printer`
  - internal helper used for `dry_run`, run logs, and warning messages
- `filelib.skill_deployer`
  - `deploy_skill`: deploy a skill folder to Copilot and/or Claude locations
  - `deploy_filelib`: deploy filelib built-in skill folder (`doc/agent`)

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

### 6) Deploy a skill to Copilot/Claude

```python
from filelib.skill_deployer import deploy_filelib, deploy_skill

# Deploy to current project's Copilot + Claude skill folders
paths = deploy_skill(
  skill_dir="doc/agent",
  destination="project",
  assistant="both",
  language="en",
  skill_name="filelib-agent",
  project_root=".",
  overwrite=True,
)
print(paths)

# Deploy to user home for Copilot only
deploy_skill(
  skill_dir="doc/agent",
  destination="home",
  assistant="copilot",
  language="zh",
  overwrite=False,
)

# Deploy filelib's built-in skill folder directly
deploy_filelib(
  destination="project",
  assistant="both",
  language="zh",
  project_root=".",
  overwrite=True,
)

# Override the deployed folder name under .../skills
deploy_filelib(
  destination="project",
  assistant="copilot",
  skill_name="my-filelib-skill",
  project_root=".",
)
```

### 7) Merge two folders without overwriting

```python
from filelib.operator import merge_folders

# Preview first (no filesystem change)
stats = merge_folders(src="backup/photos", dst="library/photos", dry_run=True)
print(stats)  # {'copied': 12, 'skipped': 5, 'renamed': 3}

# Execute with a per-file log
stats = merge_folders(src="backup/photos", dst="library/photos", run_log=True)
print(stats)
```

### 8) Copy/move a folder while preserving symbolic links

```python
from filelib.operator import copy, move

# Preview first: prints [dry-run] [RETARGET] lines for links that will be
# rewritten (also raises PermissionError here if links could not be created)
copy(src="game/mod", dst="backup/mod", preserve_symlinks=True,
     retarget_symlinks=True, dry_run=True)

# Copy: symlinks are recreated as symlinks; links whose absolute targets
# point inside "game/mod" are retargeted to point inside "backup/mod"
copy(src="game/mod", dst="backup/mod", preserve_symlinks=True,
     retarget_symlinks=True, run_log=True)

# Move: links are always preserved by the move itself; retarget_symlinks
# additionally fixes absolute in-tree links, which would otherwise dangle
move(src="game/mod", dst="backup/mod", retarget_symlinks=True, run_log=True)
```

## API Notes and Behaviors

### `scanner.ls`

- `path_type` supports:
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

### `operator.remove`

- `recursive` behavior:
  - `True`: remove directory and all contents
  - `False`: fail on non-empty directory
  - `"skip"`: skip non-empty directory
- `dry_run=True` prints intended actions without changing filesystem.

### `operator.move` and `operator.copy`

- `exist_policy`:
  - `default`: keep default behavior
  - `overwrite`: remove existing destination file first
  - `rename`: auto-generate destination suffix (`_0`, `_1`, ...)
- `make_dir=True` creates missing destination parent directories.
- `exist_policy` applies only when `dst` exists as a **file**; when `dst` is missing or an existing directory it is ignored (file/directory `src` is then placed into `dst/<basename(src)>`, or `copytree` raises `FileExistsError` for a directory `src` onto an existing directory).
- `preserve_symlinks` (`copy` only, default `False`): symlinks are kept as links instead of followed — a symlink `src` is recreated at `dst` with its original target, and links inside a copied directory tree are recreated as links (original targets unchanged).
- `retarget_symlinks` (`copy` and `move`, default `False`): with a real-directory `src`, links whose absolute targets lie inside `src` are rewritten to the corresponding location under `dst` after the copy/move. Relative links and links pointing outside the tree are kept verbatim. Single symlinks are never retargeted — only the link itself is copied/moved while its target stays valid where it is; retargeting is only sound when the whole tree containing both the link and its target is transported.
  - On `copy` it requires `preserve_symlinks=True`; otherwise a warning is printed and nothing is retargeted.
  - On `move` links are preserved by `shutil.move` itself regardless of the flag; the flag only adds retargeting (fixing links that would dangle after the move).
- Privilege pre-check: if the operation would create or rewrite at least one link, symlink-creation rights are probed **before any filesystem change**; a missing right raises `PermissionError` — in `dry_run` mode too, so previews double as feasibility checks.
- `dry_run=True` previews each rewrite as `[RETARGET] <link>: <old> -> <new>`.

### `operator.merge_folders`

- Never overwrites: on name conflict the destination file is kept, and the source file is copied under an auto-renamed name.
- Rename format is `stem_0.ext`, `stem_1.ext`, ... (same as `operator.move/copy` with `exist_policy="rename"`).
- Files are matched by relative path:
  - destination missing -> direct copy with parent directories created
  - identical SHA-256 -> skipped
  - different content or non-file destination (e.g. a directory) -> renamed copy
- Empty directories in `src` are not created in `dst`; extra files in `dst` are left untouched.
- `dry_run=True` still hashes conflicting files, so the returned statistics are accurate for the preview.
- Returns `{"copied": n, "skipped": n, "renamed": n}`.
- Raises `FileNotFoundError` if `src`/`dst` is missing; `ValueError` if a path is not a directory, or `src` and `dst` are the same folder, or `dst` is nested inside `src`.

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

### `skill_deployer.deploy_skill`

- `destination`:
  - `project` -> `<project_root>/.github/skills` (copilot), `<project_root>/.claude/skills` (claude)
  - `home` -> `~/.copilot/skills` (copilot), `~/.claude/skills` (claude)
- `assistant`: `copilot`, `claude`, or `both`
- `language`: `default|en|zh|<custom>`
  - `default/en` -> source `SKILL.md`
  - `zh` -> source `SKILL_zh.md`
  - `<custom>` -> source `SKILL_<custom>.md`
  - deployed file is always target `SKILL.md`
- `skill_name`: target skill directory name under `.../skills`
  - if provided, it is authoritative and deployed `SKILL.md` front matter `name` will be aligned to it
  - if not provided, use `name:` from selected `SKILL*.md` front matter
  - if `name:` is missing and `skill_name` is not provided, deployment raises `ValueError`
- `overwrite=True` replaces existing deployed folder
- `use_symlink=True` creates a symbolic link for target `SKILL.md`
- Deployment follows skill spec layout: `<skills_root>/<skill_name>/SKILL.md`

### `skill_deployer.deploy_filelib`

- Uses filelib built-in skill folder: `doc/agent`
- Name resolution follows `deploy_skill` rules above.

## Testing

The project includes tests under `tests/`.

Run tests with:

```bash
pytest -q
```

## Current Limitations

- `scanner.is_empty_dir` is currently a placeholder and not implemented.
- `download_response` does not create parent directories automatically.
- `merge_folders` follows directory symlinks while scanning; symlink cycles are not detected and can cause duplicated traversal or statistics.
- `move` preserves symlinks inherently (`shutil.move` behavior); `retarget_symlinks=True` only adds the in-tree retargeting pass.
- With `preserve_symlinks=True` and `exist_policy="default"`, copying a single symlink onto an existing file raises `FileExistsError` instead of silently overwriting (plain `copy2` would overwrite).
- Absolute links pointing outside the source tree are kept verbatim by the symlink flags and may dangle after a move.
- An existing destination that is a symlink is not handled by `exist_policy` (it only distinguishes file vs directory).
