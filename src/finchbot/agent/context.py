"""FinchBot 上下文构建器.

参考 Nanobot 的 ContextBuilder 设计，支持 Bootstrap 文件和技能系统。
增强动态配置、错误处理和性能优化。
"""

from pathlib import Path

from loguru import logger

from finchbot.agent.skills import SkillsLoader
from finchbot.i18n import t


class ContextBuilder:
    """上下文构建器.

    负责组装系统提示，包括 Bootstrap 文件和技能。
    支持动态配置、缓存和详细的错误处理。
    """

    # 可配置的 Bootstrap 文件列表
    DEFAULT_BOOTSTRAP_FILES = [
        "SYSTEM.md",
        "MEMORY_GUIDE.md",
        "AGENT_CONFIG.md",
        "SOUL.md",
    ]

    def __init__(self, workspace: Path, bootstrap_files: list[str] | None = None) -> None:
        """初始化上下文构建器.

        Args:
            workspace: 工作目录路径.
            bootstrap_files: 可选的 Bootstrap 文件列表，默认使用 DEFAULT_BOOTSTRAP_FILES.
        """
        self.workspace = workspace
        self.skills = SkillsLoader(workspace)
        self.bootstrap_files = bootstrap_files or self.DEFAULT_BOOTSTRAP_FILES
        self._prompt_cache: dict[str, tuple[str, float]] = {}  # 缓存键 -> (提示词, 修改时间)
        logger.debug(
            f"ContextBuilder 初始化: workspace={workspace}, bootstrap_files={self.bootstrap_files}"
        )

    def build_system_prompt(
        self, skill_names: list[str] | None = None, use_cache: bool = True
    ) -> str:
        """构建完整的系统提示词.

        Args:
            skill_names: 可选的技能名称列表.
            use_cache: 是否使用缓存.

        Returns:
            完整的系统提示词字符串.
        """
        cache_key = self._get_cache_key(skill_names)

        # 检查缓存
        if use_cache and cache_key in self._prompt_cache:
            cached_prompt, mtime = self._prompt_cache[cache_key]
            if self._check_files_unchanged(mtime):
                logger.debug("从缓存加载系统提示词")
                return cached_prompt

        logger.debug("构建系统提示词...")
        parts = []

        # 加载 Bootstrap 文件
        bootstrap = self._load_bootstrap_files()
        if bootstrap:
            parts.append(bootstrap)
            logger.debug("Bootstrap 文件加载完成")

        # 加载常驻技能
        always_skills = self.skills.get_always_skills()
        if always_skills:
            always_content = self.skills.load_skills_for_context(always_skills)
            if always_content:
                parts.append(f"# {t('agent.skills.active_skills')}\n\n{always_content}")
                logger.debug(f"加载 {len(always_skills)} 个常驻技能")

        # 加载技能摘要
        skills_summary = self.skills.build_skills_summary()
        if skills_summary:
            parts.append(f"""# {t("agent.skills.available_skills")}

{t("agent.skills.skills_intro")}
{t("agent.skills.skills_unavailable_hint")}

{skills_summary}""")
            logger.debug("技能摘要生成完成")

        # 构建最终提示词
        system_prompt = "\n\n---\n\n".join(parts)

        # 更新缓存
        if use_cache:
            current_mtime = self._get_max_file_mtime()
            self._prompt_cache[cache_key] = (system_prompt, current_mtime)
            logger.debug(f"系统提示词缓存更新，大小: {len(system_prompt)} 字符")

        return system_prompt

    def _load_bootstrap_files(self) -> str:
        """加载工作区下的 Bootstrap 文件.

        Returns:
            合并后的 Bootstrap 文件内容.
        """
        parts = []
        loaded_files = 0
        failed_files = 0

        for filename in self.bootstrap_files:
            file_path = self.workspace / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    if content.strip():
                        parts.append(f"## {filename}\n\n{content}")
                        loaded_files += 1
                        logger.debug(f"加载 Bootstrap 文件: {filename}")
                    else:
                        logger.warning(f"Bootstrap 文件为空: {filename}")
                except Exception as e:
                    failed_files += 1
                    logger.error(f"读取 Bootstrap 文件失败 {filename}: {e}")
            else:
                logger.debug(f"Bootstrap 文件不存在: {filename}")

        logger.debug(f"Bootstrap 文件加载完成: {loaded_files} 成功, {failed_files} 失败")
        return "\n\n".join(parts) if parts else ""

    def _get_cache_key(self, skill_names: list[str] | None) -> str:
        """生成缓存键.

        Args:
            skill_names: 技能名称列表.

        Returns:
            缓存键字符串.
        """
        skill_key = ",".join(sorted(skill_names)) if skill_names else "default"
        files_key = ",".join(sorted(self.bootstrap_files))
        return f"{files_key}:{skill_key}"

    def _check_files_unchanged(self, cached_mtime: float) -> bool:
        """检查文件是否未修改.

        Args:
            cached_mtime: 缓存的修改时间.

        Returns:
            文件是否未修改.
        """
        current_mtime = self._get_max_file_mtime()
        return current_mtime <= cached_mtime

    def _get_max_file_mtime(self) -> float:
        """获取所有相关文件的最大修改时间.

        Returns:
            最大修改时间.
        """
        max_mtime = 0.0

        # 检查 Bootstrap 文件
        for filename in self.bootstrap_files:
            file_path = self.workspace / filename
            if file_path.exists():
                try:
                    mtime = file_path.stat().st_mtime
                    if mtime > max_mtime:
                        max_mtime = mtime
                except Exception:
                    pass

        # 检查技能目录
        skills_dir = self.workspace / "skills"
        if skills_dir.exists():
            try:
                for skill_file in skills_dir.glob("*/SKILL.md"):
                    mtime = skill_file.stat().st_mtime
                    if mtime > max_mtime:
                        max_mtime = mtime
            except Exception:
                pass

        return max_mtime

    def clear_cache(self) -> None:
        """清除提示词缓存."""
        self._prompt_cache.clear()
        self.skills.clear_cache()
        logger.debug("上下文构建器缓存已清除")

    def get_cache_info(self) -> dict:
        """获取缓存信息.

        Returns:
            缓存信息字典.
        """
        return {
            "prompt_cache_size": len(self._prompt_cache),
            "skill_cache_info": self.skills.get_cache_info(),
            "bootstrap_files": self.bootstrap_files,
        }
