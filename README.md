# filelib

`filelib` is a lightweight Python utility library for common file workflows, including:
- directory scanning and filtering
- file/folder copy, move, and remove operations
- path resolution checks
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
  - `move`: move path with destination conflict policies
  - `copy`: copy file/folder with destination conflict policies
- `filelib.resolver`
  - `is_same_path`: compare two paths after `Path.resolve()` normalization
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
- `overwrite=True` replaces existing deployed folder
- `use_symlink=True` creates a symbolic link for target `SKILL.md`
- Deployment follows skill spec layout: `<skills_root>/<skill_name>/SKILL.md`

### `skill_deployer.deploy_filelib`

- Uses filelib built-in skill folder: `doc/agent`
- If `skill_name` is not provided:
  - first try `name:` from selected `SKILL*.md` front matter
  - fallback to `filelib-agent`

## Testing

The project includes tests under `tests/`.

Run tests with:

```bash
pytest -q
```

## Current Limitations

- `scanner.is_empty_dir` is currently a placeholder and not implemented.
- `download_response` does not create parent directories automatically.
