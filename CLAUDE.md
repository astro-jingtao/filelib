# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`filelib` is a small personal-reuse Python (>= 3.9) library of file-handling utilities: directory scanning, move/copy/remove, path/file/folder comparison, HTTP downloads, image corruption checks, folder merging, and a CLI over the core operations. Full API documentation with exact parameter semantics (`path_type`, `exist_policy`, `recursive` modes) lives in README.md — extend it when changing behavior. The agent-facing usage skill (toolkit map, behavior tables, recipes) lives in `skills/filelib/skill/SKILL.md` — consult it for how to use filelib as an agent.

## Commands

Windows/PowerShell environment. Tests must run in the `science` conda env (the one with `filelib` installed editable plus all runtime deps); the shell's default `python` is broken, so always use `conda run -n science python ...`.

- Install (editable): `pip install -e .`
- All tests: `conda run -n science python -m pytest -q`
- One test file: `conda run -n science python -m pytest tests/test_checker.py -v`
- One test: `pytest "tests/test_checker.py::TestIsSameFile::test_is_same_file_hash_mode_identical"`
- CLI smoke (after `pip install -e .`): `filelib --help`, `filelib copy --help`; without reinstalling: `python -m filelib.cli --help`
- No linter or formatter is configured.

## Architecture

- `src` layout; runtime dependencies (`requests`, `puremagic`, `image_complete`) are declared in pyproject.toml.
- One small, single-purpose module per concern under `src/filelib/`:
  - `scanner.py` — `ls()` (the package's canonical traversal API) and `is_empty_dir()` (shallow by default, `recursive=True` treats dirs holding only empty subdirs as empty)
  - `operator.py` — `remove`/`move`/`copy`/`merge_folders` with `dry_run`/`run_log`/`exist_policy`/`make_dir`
  - `checker.py` — `is_same_file`/`is_same_folder`
  - `resolver.py` — `is_same_path`
  - `downloader.py` — `download_response`
  - `identifier.py` — MIME detection + image completeness checks
  - `printer.py` — `Printer`, internal helper for dry-run/run-log/warning output used by `operator`
  - `cli.py` — argparse console entry point `filelib` (`copy|move|merge|check-image`, `main(argv) -> int`) over `operator`/`identifier`; exit codes 0/1/2, run log on by default, `copy --retarget-symlinks` implies `--preserve-symlinks`
- `__init__.py` deliberately exports only a subset (`is_same_file`, `is_same_folder`); consumers import other functions from submodules.
- Windows specifics: symlink creation needs admin/Developer Mode. Tests skip or tolerate this (`tests/test_scanner.py::_prepare_symlink_tree`).
- Known gaps (also tracked in README "Current Limitations"): `download_response` does not create parent directories; `operator.copy` has an unresolved recursion TODO.

## Conventions

These come from `.github/copilot-instructions.md` and apply to Claude Code as well:

- Prefer filelib APIs over stdlib inside package code: `scanner.ls()` over `os.walk()`/`rglob()`, `resolver.is_same_path()` over `Path.resolve()`, `operator` functions over raw `os`/`shutil` mutations. (`checker.is_same_folder` follows this by building on `scanner.ls`.)
- Absolute imports only (`from filelib.scanner import ls`), never relative imports.
- "更新文档" (update the docs) means updating both of: `README.md`, `skills/filelib/skill/SKILL.md`.
- Tests are pytest class-based and mirror modules (`test_scanner.py`, `test_operator.py`, ...); always use `tmp_path` for test files. Comments/docstrings mix English and Chinese — match the style of the file being edited.
- `TODO/` holds pending design notes (e.g. `CLI.md`, `checker.md`).
