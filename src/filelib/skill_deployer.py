from __future__ import annotations

import re
import shutil
from pathlib import Path

from filelib.printer import Printer

AssistantName = str
DestinationName = str
LanguageName = str

_SUPPORTED_ASSISTANTS = {"copilot", "claude", "both"}
_SUPPORTED_DESTINATIONS = {"home", "project"}


def deploy_filelib(
    destination: DestinationName = "project",
    assistant: AssistantName = "both",
    language: LanguageName = "default",
    skill_name: str | None = None,
    project_root: str | Path | None = None,
    overwrite: bool = False,
    use_symlink: bool = False,
) -> dict[str, str]:
    """
    Deploy filelib's built-in skill folder (``doc/agent``).

    Parameters are the same as :func:`deploy_skill`, except ``skill_dir`` is
    resolved automatically to this repository's ``doc/agent`` directory.
    """

    skill_dir = _get_filelib_skill_dir()
    return deploy_skill(
        skill_dir=skill_dir,
        destination=destination,
        assistant=assistant,
        language=language,
        skill_name=skill_name,
        project_root=project_root,
        overwrite=overwrite,
        use_symlink=use_symlink,
    )


def deploy_skill(
    skill_dir: str | Path,
    destination: DestinationName = "project",
    assistant: AssistantName = "both",
    language: LanguageName = "default",
    skill_name: str | None = None,
    project_root: str | Path | None = None,
    overwrite: bool = False,
    use_symlink: bool = False,
) -> dict[str, str]:
    """
    Deploy a skill folder to Copilot and/or Claude skill locations.

    Parameters
    ----------
    skill_dir : str | Path
        Path to a skill folder that contains ``SKILL.md``.
    destination : {'home', 'project'}, default 'project'
        Deployment scope:
        - ``home`` deploys to ``~/.copilot/skills`` and/or ``~/.claude/skills``.
        - ``project`` deploys to ``<project_root>/.github/skills`` and/or
          ``<project_root>/.claude/skills``.
    assistant : {'copilot', 'claude', 'both'}, default 'both'
        Target assistant ecosystem.
    language : str, default 'default'
        Skill language version selector:
        - ``default`` or ``en`` -> ``SKILL.md``
        - ``zh`` -> ``SKILL_zh.md``
        - other values -> ``SKILL_<language>.md``
        The selected source file is always deployed as ``SKILL.md``.
    skill_name : str | None, default None
        Target skill directory name under ``.../skills``.
        If provided, it is treated as the authoritative name and the deployed
        ``SKILL.md`` front matter ``name`` will be aligned to it.
        If None, use ``name:`` from selected source ``SKILL*.md`` front matter.
    project_root : str | Path | None, default None
        Required when ``destination='project'`` if current working directory
        is not the desired project root.
    overwrite : bool, default False
        If True, remove existing target skill folder before deployment.
    use_symlink : bool, default False
        If True, create symbolic links instead of copying files.

    Returns
    -------
    dict[str, str]
        Mapping from assistant name to deployed absolute path.

    Raises
    ------
    FileNotFoundError
        If skill folder or ``SKILL.md`` is missing.
    ValueError
        If input parameters are invalid.
    FileExistsError
        If target already exists and ``overwrite=False``.
    """

    printer = Printer(dry_run=False, run_log=False, verbose=False, ignore_warning=False)

    skill_path = Path(skill_dir).expanduser().resolve()
    if not skill_path.exists() or not skill_path.is_dir():
        raise FileNotFoundError(
            f"Skill directory does not exist: {skill_path}")

    language = language.lower().strip()
    source_skill_md = _resolve_source_skill_md(skill_path, language)
    source_text = source_skill_md.read_text(encoding="utf-8")
    md_name = _extract_front_matter_name_from_text(source_text)

    if skill_name is not None:
        give_name = _validate_skill_name(skill_name)
        resolved_skill_name = give_name
        if md_name == give_name:
            deployed_text = source_text
        else:
            deployed_text = _ensure_front_matter_name(source_text, give_name)
    else:
        if not md_name:
            raise ValueError(
                "skill_name is required when selected SKILL*.md has no front matter name"
            )
        resolved_skill_name = md_name
        deployed_text = source_text

    # only use symlink if user want to do and source and target are the same
    if use_symlink:
        if deployed_text == source_text:
            can_symlink = True
        else:
            printer.print_warning(
                "Cannot use symlink because deployed content differs from source. Falling back to copy."
            )
            can_symlink = False
    else:
        can_symlink = False

    destination = destination.lower().strip()
    assistant = assistant.lower().strip()

    if destination not in _SUPPORTED_DESTINATIONS:
        raise ValueError("destination must be 'home' or 'project'")

    if assistant not in _SUPPORTED_ASSISTANTS:
        raise ValueError("assistant must be 'copilot', 'claude', or 'both'")

    if assistant == "both":
        assistants = ["copilot", "claude"]
    else:
        assistants = [assistant]

    if destination == "home":
        root = Path.home()
    else:
        root = Path(project_root).expanduser().resolve(
        ) if project_root else Path.cwd()

    if destination == "project" and not root.exists():
        raise FileNotFoundError(f"Project root does not exist: {root}")

    deployed_paths: dict[str, str] = {}
    for item in assistants:
        target = _build_target_path(
            assistant=item,
            destination=destination,
            root=root,
            skill_name=resolved_skill_name,
        )

        _prepare_target(target, overwrite=overwrite)
        _deploy_skill_spec(
            target,
            source_skill_md=source_skill_md,
            deployed_text=deployed_text,
            use_symlink=can_symlink,
        )
        deployed_paths[item] = str(target)

    return deployed_paths


def _build_target_path(
    assistant: str,
    destination: str,
    root: Path,
    skill_name: str,
) -> Path:
    if assistant == "copilot":
        base = ".copilot/skills" if destination == "home" else ".github/skills"
    elif assistant == "claude":
        base = ".claude/skills"
    else:
        raise ValueError(f"Unsupported assistant: {assistant}")

    return (root / base / skill_name).resolve()


def _prepare_target(target: Path, overwrite: bool) -> None:
    if target.exists():
        if not overwrite:
            raise FileExistsError(
                f"Target skill already exists: {target}. Set overwrite=True to replace it."
            )
        if target.is_symlink() or target.is_file():
            target.unlink()
        else:
            shutil.rmtree(target)

    target.parent.mkdir(parents=True, exist_ok=True)


def _deploy_skill_spec(
    target: Path,
    source_skill_md: Path,
    deployed_text: str,
    use_symlink: bool,
) -> None:
    target.mkdir(parents=True, exist_ok=True)
    target_skill_md = target / "SKILL.md"

    if use_symlink:
        try:
            target_skill_md.symlink_to(source_skill_md)
        except OSError as exc:
            raise OSError(
                "Failed to create symlink. On Windows, enable Developer Mode or run with admin privileges."
            ) from exc
    else:
        target_skill_md.write_text(deployed_text, encoding="utf-8")


def _ensure_front_matter_name(content: str, skill_name: str) -> str:
    front_matter_pattern = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
    match = front_matter_pattern.match(content)

    if not match:
        header = f"---\nname: {skill_name}\n---\n\n"
        return header + content

    front_matter = match.group(1)
    body = content[match.end():]
    lines = front_matter.splitlines()

    updated = False
    for idx, line in enumerate(lines):
        if re.match(r"^\s*name\s*:", line):
            lines[idx] = f"name: {skill_name}"
            updated = True
            break

    if not updated:
        lines.append(f"name: {skill_name}")

    normalized_front_matter = "\n".join(lines)
    return f"---\n{normalized_front_matter}\n---\n{body}"


def _extract_front_matter_name_from_text(content: str) -> str | None:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if stripped.startswith("name:"):
            value = stripped.split(":", 1)[1].strip().strip("\"'")
            return _validate_skill_name(value) if value else None

    return None


def _resolve_source_skill_md(skill_path: Path, language: str) -> Path:
    if language in {"default", "en"}:
        candidate = skill_path / "SKILL.md"
    elif language == "zh":
        candidate = skill_path / "SKILL_zh.md"
    else:
        candidate = skill_path / f"SKILL_{language}.md"

    if candidate.exists() and candidate.is_file():
        return candidate

    available = sorted(path.name for path in skill_path.glob("SKILL*.md")
                       if path.is_file())
    raise FileNotFoundError(
        f"Missing language skill file: {candidate}. "
        f"Available versions in {skill_path}: {available or ['SKILL.md']}")


def _extract_front_matter_name(skill_md: Path) -> str | None:
    return _extract_front_matter_name_from_text(
        skill_md.read_text(encoding="utf-8"))


def _validate_skill_name(skill_name: str) -> str:
    normalized = skill_name.strip()
    if not normalized:
        raise ValueError("skill_name must not be empty")
    if "/" in normalized or "\\" in normalized:
        raise ValueError("skill_name must not contain path separators")
    if normalized in {".", ".."}:
        raise ValueError("skill_name must not be '.' or '..'")
    return normalized


def _get_filelib_skill_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    skill_dir = repo_root / "doc" / "agent"

    if not skill_dir.exists() or not skill_dir.is_dir():
        raise FileNotFoundError(
            "filelib built-in skill directory not found: "
            f"{skill_dir}. Use deploy_skill(skill_dir=...) to deploy a custom skill."
        )

    return skill_dir
