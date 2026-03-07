---
name: filelib-agent
description: 'Use filelib for directory scanning, path comparison, file move/copy/delete operations, HTTP downloads, and image corruption checks. Best for batch file workflows, cleanup scripts, dataset organization, and validation tasks.'
argument-hint: 'Describe your file task, for example: scan recursively and move duplicates, or detect corrupted images in a folder'
user-invocable: true
---

# Filelib Agent Skill

## When To Use
- You need to scan directories and filter files by custom rules.
- You need to move, copy, or delete files and folders with conflict control.
- You need to verify whether two paths resolve to the same real location.
- You need to download resources to local files.
- You need to detect corruption in common image formats.

## Module Capability Map
- `filelib.scanner`
  - `ls(...)`: directory scanning and filtering with recursive support and multiple path formats.
  - `is_empty_dir(...)`: currently a placeholder (`...`); do not use in automated flows.
- `filelib.resolver`
  - `is_same_path(path1, path2)`: compares paths after `Path.resolve()` normalization.
- `filelib.operator`
  - `remove(...)`: remove files/directories with `dry_run`, `run_log`, and `recursive` controls.
  - `move(...)`: move files/directories with `exist_policy`, `make_dir`, and `dry_run` controls.
  - `copy(...)`: copy files/directories with `exist_policy`, `make_dir`, and `dry_run` controls.
- `filelib.downloader`
  - `download_response(...)`: download HTTP response content to local file, returns status code.
- `filelib.identifier`
  - `get_mime_magic(...)`: MIME detection from file content.
  - `get_mime_extension(...)`: MIME detection from filename extension.
  - `is_file_corrupted(...)`: corruption check for jpeg/png/gif/bmp/webp.
- `filelib.printer`
  - `Printer`: output behavior used by operator functions for dry-run/log/warning messages.

## Critical Behavior Constraints
- `scanner.ls` actual default for `path_type` is `abs_full_path`.
- `scanner.ls` can produce duplicate names when `path_type='file_only'`.
- `operator.remove` supports `recursive` values: `True | False | 'skip'`.
- `operator.move/copy` supports `exist_policy` values: `default | overwrite | rename`.
- `operator.move/copy` requires `make_dir=True` when destination parent does not exist.
- `identifier.is_file_corrupted` return semantics:
  - `True`: file is corrupted
  - `False`: file is complete
  - `None` or custom value: unsupported MIME with `unsupported_policy='return'`
- `downloader.download_response` does not create parent directories automatically.

## Agent Procedure
1. Identify task category.
- Use `scanner.ls` for discovery and filtering.
- Use `resolver.is_same_path` for path identity checks.
- Use `operator.*` for filesystem mutations.
- Use `downloader.download_response` for network-to-file tasks.
- Use `identifier.is_file_corrupted` for image integrity checks.

2. Run a safety preview first.
- For mutation tasks, run once with `dry_run=True`.
- Set `run_log=True` to keep an auditable operation trace.

3. Handle destination conflicts.
- Prefer `exist_policy='rename'` when collisions are possible.
- Use `exist_policy='overwrite'` only when replacement is explicitly desired.

4. Handle directory prerequisites.
- Set `make_dir=True` if destination parents may be missing.
- For non-empty directory removal, explicitly choose one mode:
  - `recursive=True` to delete all contents
  - `recursive='skip'` to keep non-empty directories
  - `recursive=False` to fail fast

5. Execute and verify.
- Re-scan with `scanner.ls` or verify with `Path.exists()` after execution.

## Common Recipes

### 1) Scan image files recursively
```python
from filelib.scanner import ls

files = ls(
    directory='data/images',
    match_func=lambda f: f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')),
    recursive=True,
    path_type='abs_full_path'
)
```

### 2) Detect corrupted images
```python
from filelib.identifier import is_file_corrupted

corrupted = []
for p in files:
    # True means corrupted
    if is_file_corrupted(p, mime_method='magic', unsupported_policy='return', unsupported_return=None):
        corrupted.append(p)
```

### 3) Safe move flow (dry-run then execute)
```python
from filelib.operator import move

# Preview
move('a/source.txt', 'b/target.txt', dry_run=True, run_log=True, exist_policy='rename', make_dir=True)

# Execute
move('a/source.txt', 'b/target.txt', dry_run=False, run_log=True, exist_policy='rename', make_dir=True)
```

### 4) Conservative directory removal
```python
from filelib.operator import remove

# Skip non-empty directories
remove('tmp/cache', recursive='skip', dry_run=False, run_log=True)
```

### 5) Download with existing-file protection
```python
from filelib.downloader import download_response

status = download_response(
    url='https://example.com/archive.zip',
    filename='downloads/archive.zip',
    force=False,
    verbose=True,
    timeout=30
)
```

## Failure Handling
- `FileNotFoundError`:
  - Confirm source path exists.
  - Add `make_dir=True` for `move/copy` if parent path is missing.
- `ValueError: exist_policy must be ...`:
  - Use one of `default`, `overwrite`, or `rename`.
- `Invalid path_type`:
  - Use one of `file_only`, `raw_full_path`, `abs_full_path`, or `rel_path`.
- Unsupported MIME errors:
  - Use `unsupported_policy='return'` with `unsupported_return`, or pre-filter by extension.

## Notes
- This skill reflects the current repository implementation directly.
- `scanner.is_empty_dir` is not implemented yet; do not include it in automation until implemented.
- For automatic VS Code skill discovery, you can mirror this file to `.github/skills/filelib-agent/SKILL.md`.
