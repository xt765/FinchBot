"""FinchBot 技能加载器.

参考 Nanobot 的 SkillsLoader 设计，实现渐进式技能加载、依赖检查等功能。
增强错误处理、验证和日志记录。
"""

import json
import os
import re
import shutil
from pathlib import Path

from loguru import logger

BUILTIN_SKILLS_DIR = Path(__file__).parent.parent / "skills"


class SkillsLoader:
    """技能加载器.

    负责加载和管理 Agent 技能，支持内置技能和工作区技能。
    提供详细的错误处理、验证和性能优化。
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
        self._skill_cache: dict[str, tuple[str, float]] = {}  # 技能名称 -> (内容, 修改时间)
        logger.debug(
            f"SkillsLoader 初始化: workspace={workspace}, builtin_skills={self.builtin_skills}"
        )

    def list_skills(self, filter_unavailable: bool = True) -> list[dict[str, str]]:
        """列出所有可用技能.

        Args:
            filter_unavailable: 是否过滤掉依赖不满足的技能.

        Returns:
            技能信息列表，每个元素包含 name、path、source.
        """
        skills = []
        logger.debug("开始扫描可用技能...")

        # 扫描工作区技能
        if self.workspace_skills.exists():
            logger.debug(f"扫描工作区技能目录: {self.workspace_skills}")
            for skill_dir in self.workspace_skills.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists():
                        try:
                            # 验证技能文件格式
                            if self._validate_skill_file(skill_file):
                                skills.append(
                                    {
                                        "name": skill_dir.name,
                                        "path": str(skill_file),
                                        "source": "workspace",
                                    }
                                )
                                logger.debug(f"发现工作区技能: {skill_dir.name}")
                        except Exception as e:
                            logger.warning(f"技能文件验证失败 {skill_file}: {e}")
                    else:
                        logger.debug(f"技能目录缺少 SKILL.md: {skill_dir}")
        else:
            logger.debug(f"工作区技能目录不存在: {self.workspace_skills}")

        # 扫描内置技能
        if self.builtin_skills and self.builtin_skills.exists():
            logger.debug(f"扫描内置技能目录: {self.builtin_skills}")
            for skill_dir in self.builtin_skills.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    # 检查是否已存在同名技能（工作区技能优先）且文件存在
                    if skill_file.exists() and not any(s["name"] == skill_dir.name for s in skills):
                        try:
                            # 验证技能文件格式
                            if self._validate_skill_file(skill_file):
                                skills.append(
                                    {
                                        "name": skill_dir.name,
                                        "path": str(skill_file),
                                        "source": "builtin",
                                    }
                                )
                                logger.debug(f"发现内置技能: {skill_dir.name}")
                        except Exception as e:
                            logger.warning(f"技能文件验证失败 {skill_file}: {e}")
        else:
            logger.debug(f"内置技能目录不存在: {self.builtin_skills}")

        logger.debug(f"共发现 {len(skills)} 个技能")

        if filter_unavailable:
            available_skills = []
            for skill in skills:
                skill_meta = self._get_skill_meta(skill["name"])
                if self._check_requirements(skill_meta):
                    available_skills.append(skill)
                else:
                    missing = self._get_missing_requirements(skill_meta)
                    logger.debug(f"技能 '{skill['name']}' 依赖不满足: {missing}")
            logger.debug(f"过滤后剩余 {len(available_skills)} 个可用技能")
            return available_skills

        return skills

    def load_skill(self, name: str, use_cache: bool = True) -> str | None:
        """加载指定技能.

        Args:
            name: 技能名称（目录名）.
            use_cache: 是否使用缓存.

        Returns:
            技能内容字符串，未找到则返回 None.
        """
        logger.debug(f"加载技能: {name}, use_cache={use_cache}")

        # 检查缓存
        if use_cache and name in self._skill_cache:
            content, mtime = self._skill_cache[name]
            # 检查文件是否已修改
            file_path = self._get_skill_file_path(name)
            if file_path and file_path.exists():
                current_mtime = file_path.stat().st_mtime
                if current_mtime <= mtime:
                    logger.debug(f"从缓存加载技能: {name}")
                    return content
                else:
                    logger.debug(f"技能文件已修改，清除缓存: {name}")

        # 首先检查工作区技能
        workspace_skill = self.workspace_skills / name / "SKILL.md"
        if workspace_skill.exists():
            try:
                content = workspace_skill.read_text(encoding="utf-8")
                # 验证内容格式
                if self._validate_skill_content(content):
                    # 更新缓存
                    mtime = workspace_skill.stat().st_mtime
                    self._skill_cache[name] = (content, mtime)
                    logger.debug(f"从工作区加载技能: {name}")
                    return content
                else:
                    logger.warning(f"技能内容格式无效: {name}")
            except Exception as e:
                logger.error(f"读取工作区技能失败 {workspace_skill}: {e}")
                return None

        # 然后检查内置技能
        if self.builtin_skills:
            builtin_skill = self.builtin_skills / name / "SKILL.md"
            if builtin_skill.exists():
                try:
                    content = builtin_skill.read_text(encoding="utf-8")
                    # 验证内容格式
                    if self._validate_skill_content(content):
                        # 更新缓存
                        mtime = builtin_skill.stat().st_mtime
                        self._skill_cache[name] = (content, mtime)
                        logger.debug(f"从内置技能加载: {name}")
                        return content
                    else:
                        logger.warning(f"技能内容格式无效: {name}")
                except Exception as e:
                    logger.error(f"读取内置技能失败 {builtin_skill}: {e}")
                    return None

        logger.warning(f"技能未找到: {name}")
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

    def _get_skill_file_path(self, name: str) -> Path | None:
        """获取技能文件路径.

        Args:
            name: 技能名称.

        Returns:
            技能文件路径，未找到则返回 None.
        """
        # 首先检查工作区技能
        workspace_skill = self.workspace_skills / name / "SKILL.md"
        if workspace_skill.exists():
            return workspace_skill

        # 然后检查内置技能
        if self.builtin_skills:
            builtin_skill = self.builtin_skills / name / "SKILL.md"
            if builtin_skill.exists():
                return builtin_skill

        return None

    def _validate_skill_file(self, file_path: Path) -> bool:
        """验证技能文件格式.

        Args:
            file_path: 技能文件路径.

        Returns:
            文件格式是否有效.
        """
        try:
            if not file_path.exists():
                logger.warning(f"技能文件不存在: {file_path}")
                return False

            # 检查文件大小（防止过大文件）
            file_size = file_path.stat().st_size
            if file_size > 10 * 1024 * 1024:  # 10MB
                logger.warning(f"技能文件过大: {file_path} ({file_size} bytes)")
                return False

            # 检查文件扩展名
            if file_path.suffix.lower() != ".md":
                logger.warning(f"技能文件扩展名无效: {file_path}")
                return False

            # 读取并验证内容
            content = file_path.read_text(encoding="utf-8")
            return self._validate_skill_content(content)

        except Exception as e:
            logger.error(f"技能文件验证失败 {file_path}: {e}")
            return False

    def _validate_skill_content(self, content: str) -> bool:
        """验证技能内容格式.

        Args:
            content: 技能内容字符串.

        Returns:
            内容格式是否有效.
        """
        if not content or not content.strip():
            logger.warning("技能内容为空")
            return False

        # 检查是否包含必要的 frontmatter
        if not content.startswith("---"):
            logger.warning("技能内容缺少 YAML frontmatter")
            return False

        # 解析 frontmatter
        try:
            frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if not frontmatter_match:
                logger.warning("技能 frontmatter 格式无效")
                return False

            frontmatter = frontmatter_match.group(1)
            metadata = {}
            for line in frontmatter.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip().strip("\"'")

            # 检查必需字段
            if "name" not in metadata:
                logger.warning("技能 frontmatter 缺少 'name' 字段")
                return False

            if "description" not in metadata:
                logger.warning("技能 frontmatter 缺少 'description' 字段")
                return False

            # 检查 metadata 字段格式
            if "metadata" in metadata:
                try:
                    metadata_json = json.loads(metadata["metadata"])
                    if not isinstance(metadata_json, dict):
                        logger.warning("技能 metadata 字段格式无效")
                        return False
                except json.JSONDecodeError:
                    logger.warning("技能 metadata 字段 JSON 格式无效")
                    return False

            # 检查内容部分是否为空
            content_without_frontmatter = content[frontmatter_match.end() :].strip()
            if not content_without_frontmatter:
                logger.warning("技能内容部分为空")
                return False

            return True

        except Exception as e:
            logger.error(f"技能内容验证失败: {e}")
            return False

    def clear_cache(self) -> None:
        """清除技能缓存."""
        self._skill_cache.clear()
        logger.debug("技能缓存已清除")

    def get_cache_info(self) -> dict:
        """获取缓存信息.

        Returns:
            缓存信息字典.
        """
        return {
            "cache_size": len(self._skill_cache),
            "cached_skills": list(self._skill_cache.keys()),
            "cache_hits": getattr(self, "_cache_hits", 0),
            "cache_misses": getattr(self, "_cache_misses", 0),
        }
