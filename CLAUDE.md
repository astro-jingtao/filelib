# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`filelib` is a small personal-reuse Python (>= 3.9) library of file-handling utilities: directory scanning, move/copy/remove, path/file/folder comparison, HTTP downloads, image corruption checks, and deployment of AI-agent skills. Full API documentation with exact parameter semantics (`path_type`, `exist_policy`, `recursive` modes, skill name resolution) lives in README.md — extend it when changing behavior.

## Commands

Windows/PowerShell environment. No specific conda environment is required; run pytest in whichever env the package is installed in.

- Install (editable): `pip install -e .`
- All tests: `pytest -q`
- One test file: `pytest tests/test_checker.py -v`
- One test: `pytest "tests/test_checker.py::TestIsSameFile::test_is_same_file_hash_mode_identical"`
- No linter or formatter is configured.

## Architecture

- `src` layout; runtime dependencies (`requests`, `puremagic`, `image_complete`) are declared in pyproject.toml.
- One small, single-purpose module per concern under `src/filelib/`:
  - `scanner.py` — `ls()`, the package's canonical traversal API
  - `operator.py` — `remove`/`move`/`copy` with `dry_run`/`run_log`/`exist_policy`/`make_dir`
  - `checker.py` — `is_same_file`/`is_same_folder`
  - `resolver.py` — `is_same_path`
  - `downloader.py` — `download_response`
  - `identifier.py` — MIME detection + image completeness checks
  - `printer.py` — `Printer`, internal helper for dry-run/run-log/warning output used by `operator`
  - `skill_deployer.py` — `deploy_skill`/`deploy_filelib`
- `__init__.py` deliberately exports only a subset (`deploy_skill`, `deploy_filelib`, `is_same_file`, `is_same_folder`); consumers import other functions from submodules.
- `skill_deployer` deploys the built-in skill folder `doc/agent/` (`SKILL.md` + `SKILL_zh.md`) to Copilot (`<root>/.github/skills` or `~/.copilot/skills`) and/or Claude (`<root>/.claude/skills` or `~/.claude/skills`). `_get_filelib_skill_dir()` locates the repo root via `Path(__file__).parents[2]`, which assumes the src layout — keep this in mind when refactoring.
- Windows specifics: symlink creation needs admin/Developer Mode. Tests skip or tolerate this (`tests/test_scanner.py::_prepare_symlink_tree`, `tests/test_skill_deployer.py::test_project_symlink`).
- Known gaps (also tracked in README "Current Limitations"): `scanner.is_empty_dir` is a `...` placeholder; `download_response` does not create parent directories; `operator.copy` has an unresolved recursion TODO.

## Conventions

These come from `.github/copilot-instructions.md` and apply to Claude Code as well:

- Prefer filelib APIs over stdlib inside package code: `scanner.ls()` over `os.walk()`/`rglob()`, `resolver.is_same_path()` over `Path.resolve()`, `operator` functions over raw `os`/`shutil` mutations. (`checker.is_same_folder` follows this by building on `scanner.ls`.)
- Absolute imports only (`from filelib.scanner import ls`), never relative imports.
- "更新文档" (update the docs) means updating all three of: `README.md`, `doc/agent/SKILL.md`, `doc/agent/SKILL_zh.md`.
- Tests are pytest class-based and mirror modules (`test_scanner.py`, `test_operator.py`, ...); always use `tmp_path` for test files. Comments/docstrings mix English and Chinese — match the style of the file being edited.
- `TODO/` holds pending design notes (e.g., a planned `filelib-deploy-skill` CLI for `deploy_filelib`).
