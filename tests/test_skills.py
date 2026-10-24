"""Tests for the skills tree shipped as package data under filelib.skills."""

from pathlib import Path
import runpy

import filelib.skills as skills_pkg


class TestSkillsTree:
    def test_skill_files_present_in_package(self):
        """skill 容器与部署指南随包存在（安装后 skills 目录为空属落地缺陷）"""
        root = Path(skills_pkg.__file__).parent

        assert (root / "SKILL-DEPLOY.md").is_file()
        assert (root / "filelib" / "meta.yaml").is_file()
        assert (root / "filelib" / "skill" / "SKILL.md").is_file()
        assert (root / "filelib" / "skill" / "CHANGELOG.md").is_file()

    def test_discovery_entry_prints_root_and_guide(self, capsys):
        """python -m filelib.skills 打印 skills 根路径与部署指南指针"""
        runpy.run_module("filelib.skills", run_name="__main__")

        out = capsys.readouterr().out.strip().splitlines()
        root = Path(out[0]).resolve()
        assert root == Path(skills_pkg.__file__).parent.resolve()
        assert out[1] == f"Deployment guide: {root / 'SKILL-DEPLOY.md'}"
