"""FinchBot 上下文构建器.

参考 Nanobot 的 ContextBuilder 设计，支持 Bootstrap 文件和技能系统。
"""

from pathlib import Path

from finchbot.agent.skills import SkillsLoader

BOOTSTRAP_FILES = [
    "AGENTS.md",
    "SOUL.md",
    "USER.md",
    "TOOLS.md",
    "IDENTITY.md",
]


class ContextBuilder:
    """上下文构建器.

    负责组装系统提示，包括 Bootstrap 文件和技能。
    """

    def __init__(self, workspace: Path) -> None:
        """初始化上下文构建器.

        Args:
            workspace: 工作目录路径.
        """
        self.workspace = workspace
        self.skills = SkillsLoader(workspace)

    def build_system_prompt(self, skill_names: list[str] | None = None) -> str:
        """构建完整的系统提示词.

        Args:
            skill_names: 可选的技能名称列表.

        Returns:
            完整的系统提示词字符串.
        """
        parts = []

        bootstrap = self._load_bootstrap_files()
        if bootstrap:
            parts.append(bootstrap)

        always_skills = self.skills.get_always_skills()
        if always_skills:
            always_content = self.skills.load_skills_for_context(always_skills)
            if always_content:
                parts.append(f"# Active Skills\n\n{always_content}")

        skills_summary = self.skills.build_skills_summary()
        if skills_summary:
            parts.append(f"""# Skills

The following skills extend your capabilities. To use a skill, read its SKILL.md file using the read_file tool.
Skills with available="false" need dependencies installed first.

{skills_summary}""")

        return "\n\n---\n\n".join(parts)

    def _load_bootstrap_files(self) -> str:
        """加载工作区下的 Bootstrap 文件.

        Returns:
            合并后的 Bootstrap 文件内容.
        """
        parts = []

        for filename in BOOTSTRAP_FILES:
            file_path = self.workspace / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    if content.strip():
                        parts.append(f"## {filename}\n\n{content}")
                except Exception:
                    pass

        return "\n\n".join(parts) if parts else ""

