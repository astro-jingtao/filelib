from pathlib import Path

import pytest

import filelib.skill_deployer as skill_deployer_module
from filelib.skill_deployer import deploy_filelib, deploy_skill


class TestDeploySkill:

    @pytest.fixture(autouse=True)
    def setup_tmpdir(self, tmp_path: Path):
        self.skill_dir = tmp_path / "demo_skill"
        self.skill_dir.mkdir()
        (self.skill_dir / "SKILL.md").write_text("# Demo skill\n")
        (self.skill_dir / "SKILL_zh.md").write_text("# 演示技能\n")
        (self.skill_dir / "notes.txt").write_text("extra content\n")

        self.project_root = tmp_path / "project"
        self.project_root.mkdir()

        yield

    def test_deploy_project_both_copy(self) -> None:
        deployed = deploy_skill(
            skill_dir=self.skill_dir,
            destination="project",
            assistant="both",
            project_root=self.project_root,
        )

        copilot_target = (
            self.project_root / ".github" / "skills" / self.skill_dir.name
        ).resolve()
        claude_target = (
            self.project_root / ".claude" / "skills" / self.skill_dir.name
        ).resolve()

        assert deployed == {
            "copilot": str(copilot_target),
            "claude": str(claude_target),
        }
        assert (copilot_target / "SKILL.md").exists()
        assert (claude_target / "SKILL.md").exists()
        assert (copilot_target / "SKILL.md").read_text() == "# Demo skill\n"
        assert not (copilot_target / "notes.txt").exists()

    def test_existing_target_without_overwrite_raises(self) -> None:
        deploy_skill(
            skill_dir=self.skill_dir,
            destination="project",
            assistant="copilot",
            project_root=self.project_root,
        )

        with pytest.raises(FileExistsError):
            deploy_skill(
                skill_dir=self.skill_dir,
                destination="project",
                assistant="copilot",
                project_root=self.project_root,
                overwrite=False,
            )

    def test_project_symlink(self) -> None:
        deployed = deploy_skill(
            skill_dir=self.skill_dir,
            destination="project",
            assistant="copilot",
            project_root=self.project_root,
            use_symlink=True,
        )

        target = Path(deployed["copilot"])
        target_skill_md = target / "SKILL.md"
        assert target.is_dir()
        assert target_skill_md.is_symlink()
        assert target_skill_md.resolve() == (self.skill_dir / "SKILL.md").resolve()

    def test_language_zh_deployed_as_skill_md(self) -> None:
        deployed = deploy_skill(
            skill_dir=self.skill_dir,
            destination="project",
            assistant="copilot",
            language="zh",
            project_root=self.project_root,
        )

        target = Path(deployed["copilot"])
        assert (target / "SKILL.md").read_text() == "# 演示技能\n"

    def test_missing_language_version_raises(self) -> None:
        with pytest.raises(FileNotFoundError, match="Missing language skill file"):
            deploy_skill(
                skill_dir=self.skill_dir,
                destination="project",
                assistant="copilot",
                language="ja",
                project_root=self.project_root,
            )

    def test_custom_skill_name(self) -> None:
        deployed = deploy_skill(
            skill_dir=self.skill_dir,
            destination="project",
            assistant="copilot",
            skill_name="my-filelib-skill",
            project_root=self.project_root,
        )

        target = Path(deployed["copilot"])
        assert target.name == "my-filelib-skill"
        assert (target / "SKILL.md").exists()


class TestDeployFilelib:

    @pytest.fixture(autouse=True)
    def setup_tmpdir(self, tmp_path: Path):
        self.skill_dir = tmp_path / "demo_skill"
        self.skill_dir.mkdir()
        (self.skill_dir / "SKILL.md").write_text("# Demo skill\n")
        (self.skill_dir / "SKILL_zh.md").write_text("# 演示技能\n")

        self.project_root = tmp_path / "project"
        self.project_root.mkdir()

        yield

    def test_uses_builtin_skill_dir(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            skill_deployer_module,
            "_get_filelib_skill_dir",
            lambda: self.skill_dir,
        )

        deployed = deploy_filelib(
            destination="project",
            assistant="copilot",
            project_root=self.project_root,
        )

        target = (self.project_root / ".github" / "skills" / "filelib-agent").resolve()
        assert deployed == {"copilot": str(target)}
        assert (target / "SKILL.md").exists()

    def test_uses_language_version(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            skill_deployer_module,
            "_get_filelib_skill_dir",
            lambda: self.skill_dir,
        )

        deployed = deploy_filelib(
            destination="project",
            assistant="copilot",
            language="zh",
            project_root=self.project_root,
        )

        target = Path(deployed["copilot"])
        assert target.name == "filelib-agent"
        assert (target / "SKILL.md").read_text() == "# 演示技能\n"

    def test_custom_skill_name_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            skill_deployer_module,
            "_get_filelib_skill_dir",
            lambda: self.skill_dir,
        )

        deployed = deploy_filelib(
            destination="project",
            assistant="copilot",
            skill_name="my-skill",
            project_root=self.project_root,
        )

        target = Path(deployed["copilot"])
        assert target.name == "my-skill"
        assert (target / "SKILL.md").exists()

    def test_auto_skill_name_from_front_matter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        (self.skill_dir / "SKILL.md").write_text(
            "---\nname: frontmatter-skill\n---\n\n# Demo skill\n"
        )
        monkeypatch.setattr(
            skill_deployer_module,
            "_get_filelib_skill_dir",
            lambda: self.skill_dir,
        )

        deployed = deploy_filelib(
            destination="project",
            assistant="copilot",
            project_root=self.project_root,
        )

        target = Path(deployed["copilot"])
        assert target.name == "frontmatter-skill"

    def test_missing_builtin_skill_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def _raise_missing() -> Path:
            raise FileNotFoundError("missing built-in skill")

        monkeypatch.setattr(
            skill_deployer_module,
            "_get_filelib_skill_dir",
            _raise_missing,
        )

        with pytest.raises(FileNotFoundError, match="missing built-in skill"):
            deploy_filelib()
