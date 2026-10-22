# Changelog — filelib

Notable changes, newest first.

## 2026-10-22

### Changed
- Skills root moved from the repository root into the package (`filelib.skills` under the src layout): the installed distribution now carries the skill as package data, with the `python -m filelib.skills` discovery entry.
- Deployment guide rewritten for the installed-package consumer — links point at the installed `<skills-root>/<name>/skill`, never a repository checkout.
- `operator.dry_run_session` coverage: toolkit row and a Destinations note on batch dry-run previews sharing virtual created-directory state.

### Added
- Initial skill — agent guide to the filelib package: toolkit map, behavior tables for scanning, destinations, deletion, symlinks, merging, comparison, downloads, and image checks, CLI mirroring, recipes, failure shapes, limits.
- `meta.yaml` declaring the `filelib` console-script requirement.
- Deployment guide `SKILL-DEPLOY.md` beside the skill containers.
