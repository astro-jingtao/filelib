from __future__ import annotations

import shutil
from pathlib import Path


AssistantName = str
DestinationName = str

_SUPPORTED_ASSISTANTS = {"copilot", "claude", "both"}
_SUPPORTED_DESTINATIONS = {"home", "project"}


def deploy_skill(
    skill_dir: str | Path,
    destination: DestinationName = "project",
    assistant: AssistantName = "both",
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

    skill_path = Path(skill_dir).expanduser().resolve()
    if not skill_path.exists() or not skill_path.is_dir():
        raise FileNotFoundError(f"Skill directory does not exist: {skill_path}")

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"Missing SKILL.md in skill directory: {skill_path}")

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
        root = Path(project_root).expanduser().resolve() if project_root else Path.cwd()

    if destination == "project" and not root.exists():
        raise FileNotFoundError(f"Project root does not exist: {root}")

    deployed_paths: dict[str, str] = {}
    for item in assistants:
        target = _build_target_path(
            assistant=item,
            destination=destination,
            root=root,
            skill_name=skill_path.name,
        )

        _prepare_target(target, overwrite=overwrite)
        _deploy_folder(skill_path, target, use_symlink=use_symlink)
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


def _deploy_folder(skill_path: Path, target: Path, use_symlink: bool) -> None:
    if use_symlink:
        try:
            target.symlink_to(skill_path, target_is_directory=True)
        except OSError as exc:
            raise OSError(
                "Failed to create symlink. On Windows, enable Developer Mode or run with admin privileges."
            ) from exc
    else:
        shutil.copytree(skill_path, target)