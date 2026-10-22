# Copilot Instructions

Repository conventions:

- Run tests in conda environment `science` (not `base`).
- In this repo, "更新文档" means updating both of:
  - `README.md`
  - `skills/filelib/skill/SKILL.md`

## Code Style Guidelines

### Prioritize Package APIs Over stdlib

When implementing features in `filelib`, prefer using APIs from this package over Python's standard library when:
1. **Directory traversal**: Use `filelib.scanner.ls()` instead of `os.walk()`, `pathlib.rglob()`, or similar.
2. **Path operations**: Use `filelib.resolver.is_same_path()` for path comparison instead of direct `Path.resolve()`.
3. **File operations**: Use `filelib.operator` (remove, copy, move) for filesystem mutations.

**Benefits**:
- Consistent behavior and error handling across the package
- Centralized maintenance of patterns and edge cases
- Better test coverage through package-level testing

**Example**:
```python
# ✓ Preferred
from filelib.scanner import ls
files = ls(directory=folder, recursive=True, path_type='rel_path')

# ✗ Avoid
files = [p for p in folder.rglob('*') if p.is_file()]
```

### Import Style – Absolute Imports Only

Use absolute imports for all `filelib` module imports, never relative imports:

```python
# ✓ Preferred – absolute imports
from filelib.scanner import ls
from filelib.operator import remove
from filelib.checker import is_same_file

# ✗ Avoid – relative imports
from .scanner import ls
from . import operator
```

**Benefits**:
- Clearer module dependency chain
- More consistent with package usage from outside
- Easier to re-organize modules without breaking referential integrity
- Aligns with how external consumers import from filelib
