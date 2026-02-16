"""FinchBot 技能加载器.

参考 Nanobot 的 SkillsLoader 设计，实现渐进式技能加载、依赖检查等功能。
"""

import json
import os
import re
import shutil
from pathlib import Path

BUILTIN_SKILLS_DIR = Path(__file__).parent.parent / "skills"


class SkillsLoader:
    """技能加载器.

    负责加载和管理 Agent 技能，支持内置技能和工作区技能。
    """

    def __init__(self, workspace: Path, builtin_skills_dir: Path | None = None) -> None:
        """初始化技能加载器.

        Args:
            workspace: 工作目录路径.
            builtin_skills_dir: 可选的内置技能目录路径.
        """
        self.workspace = workspace
        self.workspace_skills = workspace / "skills"
        self.builtin_skills = builtin_skills_dir or BUILTIN_SKILLS_DIR

    def list_skills(self, filter_unavailable: bool = True) -> list[dict[str, str]]:
        """列出所有可用技能.

        Args:
            filter_unavailable: 是否过滤掉依赖不满足的技能.

        Returns:
            技能信息列表，每个元素包含 name、path、source.
        """
        skills = []

        if self.workspace_skills.exists():
            for skill_dir in self.workspace_skills.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists():
                        skills.append(
                            {"name": skill_dir.name, "path": str(skill_file), "source": "workspace"}
                        )

        if self.builtin_skills and self.builtin_skills.exists():
            for skill_dir in self.builtin_skills.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists() and not any(s["name"] == skill_dir.name for s in skills):
                        skills.append(
                            {"name": skill_dir.name, "path": str(skill_file), "source": "builtin"}
                        )

        if filter_unavailable:
            return [s for s in skills if self._check_requirements(self._get_skill_meta(s["name"]))]
        return skills

    def load_skill(self, name: str) -> str | None:
        """加载指定技能.

        Args:
            name: 技能名称（目录名）.

        Returns:
            技能内容字符串，未找到则返回 None.
        """
        workspace_skill = self.workspace_skills / name / "SKILL.md"
        if workspace_skill.exists():
            return workspace_skill.read_text(encoding="utf-8")

        if self.builtin_skills:
            builtin_skill = self.builtin_skills / name / "SKILL.md"
            if builtin_skill.exists():
                return builtin_skill.read_text(encoding="utf-8")

        return None

    def load_skills_for_context(self, skill_names: list[str]) -> str:
        """加载指定技能用于 Agent 上下文.

        Args:
            skill_names: 技能名称列表.

        Returns:
            格式化后的技能内容字符串.
        """
        parts = []
        for name in skill_names:
            content = self.load_skill(name)
            if content:
                content = self._strip_frontmatter(content)
                parts.append(f"### Skill: {name}\n\n{content}")

        return "\n\n---\n\n".join(parts) if parts else ""

    def build_skills_summary(self) -> str:
        """构建技能摘要（XML 格式）.

        用于渐进式加载，Agent 可以在需要时用 read_file 读取完整内容.

        Returns:
            XML 格式的技能摘要.
        """
        all_skills = self.list_skills(filter_unavailable=False)
        if not all_skills:
            return ""

        def escape_xml(s: str) -> str:
            return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        lines = ["<skills>"]
        for s in all_skills:
            name = escape_xml(s["name"])
            path = s["path"]
            desc = escape_xml(self._get_skill_description(s["name"]))
            skill_meta = self._get_skill_meta(s["name"])
            available = self._check_requirements(skill_meta)

            lines.append(f'  <skill available="{str(available).lower()}">')
            lines.append(f"    <name>{name}</name>")
            lines.append(f"    <description>{desc}</description>")
            lines.append(f"    <location>{path}</location>")

            if not available:
                missing = self._get_missing_requirements(skill_meta)
                if missing:
                    lines.append(f"    <requires>{escape_xml(missing)}</requires>")

            lines.append("  </skill>")
        lines.append("</skills>")

        return "\n".join(lines)

    def get_always_skills(self) -> list[str]:
        """获取标记为 always=true 且依赖满足的技能.

        Returns:
            常驻技能名称列表.
        """
        result = []
        for s in self.list_skills(filter_unavailable=True):
            meta = self.get_skill_metadata(s["name"]) or {}
            skill_meta = self._parse_finchbot_metadata(meta.get("metadata", ""))
            if skill_meta.get("always") or meta.get("always"):
                result.append(s["name"])
        return result

    def get_skill_metadata(self, name: str) -> dict | None:
        """从技能的 frontmatter 中获取元数据.

        Args:
            name: 技能名称.

        Returns:
            元数据字典，未找到则返回 None.
        """
        content = self.load_skill(name)
        if not content:
            return None

        if content.startswith("---"):
            match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if match:
                metadata = {}
                for line in match.group(1).split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip().strip("\"'")
                return metadata

        return None

    def _strip_frontmatter(self, content: str) -> str:
        """移除 Markdown 内容中的 YAML frontmatter.

        Args:
            content: 技能内容.

        Returns:
            移除 frontmatter 后的内容.
        """
        if content.startswith("---"):
            match = re.match(r"^---\n.*?\n---\n", content, re.DOTALL)
            if match:
                return content[match.end() :].strip()
        return content

    def _get_skill_description(self, name: str) -> str:
        """从技能的 frontmatter 中获取描述.

        Args:
            name: 技能名称.

        Returns:
            技能描述字符串.
        """
        meta = self.get_skill_metadata(name)
        if meta and meta.get("description"):
            return meta["description"]
        return name

    def _parse_finchbot_metadata(self, raw: str) -> dict:
        """解析 frontmatter 中的 finchbot 元数据 JSON.

        Args:
            raw: 原始元数据字符串.

        Returns:
            解析后的 finchbot 元数据字典.
        """
        try:
            data = json.loads(raw)
            return data.get("finchbot", {}) if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def _get_skill_meta(self, name: str) -> dict:
        """获取技能的 finchbot 元数据.

        Args:
            name: 技能名称.

        Returns:
            finchbot 元数据字典.
        """
        meta = self.get_skill_metadata(name) or {}
        return self._parse_finchbot_metadata(meta.get("metadata", ""))

    def _check_requirements(self, skill_meta: dict) -> bool:
        """检查技能依赖是否满足.

        Args:
            skill_meta: 技能元数据字典.

        Returns:
            依赖是否满足.
        """
        requires = skill_meta.get("requires", {})
        for b in requires.get("bins", []):
            if not shutil.which(b):
                return False
        for env in requires.get("env", []):
            if not os.environ.get(env):
                return False
        return True

    def _get_missing_requirements(self, skill_meta: dict) -> str:
        """获取缺失的依赖描述.

        Args:
            skill_meta: 技能元数据字典.

        Returns:
            缺失依赖的描述字符串.
        """
        missing = []
        requires = skill_meta.get("requires", {})
        for b in requires.get("bins", []):
            if not shutil.which(b):
                missing.append(f"CLI: {b}")
        for env in requires.get("env", []):
            if not os.environ.get(env):
                missing.append(f"ENV: {env}")
        return ", ".join(missing)
