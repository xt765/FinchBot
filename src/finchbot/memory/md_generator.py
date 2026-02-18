"""MD文件生成器.

作为记忆系统的视图层，负责从数据库生成人类可读的MD文件。
提供动态MD文件生成功能，保证MD文件与数据库数据一致。

TODO: 未使用 - 当前仅在测试中使用，考虑集成到CLI工具或作为可选功能模块。
      功能完整且有潜在价值，可用于生成用户友好的记忆报告。
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from loguru import logger

from finchbot.memory.manager import MemoryManager


class MDFileGenerator:
    """MD文件生成器.

    负责从数据库生成各种MD文件：
    1. MEMORY.md - 长期记忆摘要
    2. daily/YYYY-MM-DD.md - 每日笔记
    3. categories/*.md - 分类视图
    """

    def __init__(self, workspace: Path) -> None:
        """初始化MD文件生成器.

        Args:
            workspace: 工作目录路径。
        """
        self.workspace = workspace
        self.memory_dir = workspace / "memory"
        self.daily_dir = self.memory_dir / "daily"
        self.categories_dir = self.memory_dir / "categories"

        # 创建必要的目录
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        self.categories_dir.mkdir(parents=True, exist_ok=True)

        # 初始化内存管理器
        self.manager = MemoryManager(workspace)

        # 缓存机制
        self.cache = {}
        self.cache_ttl = 300  # 5分钟缓存时间

        logger.info(f"MDFileGenerator initialized at {self.workspace}")

    def generate_memory_md(self) -> str:
        """生成MEMORY.md文件.

        Returns:
            MD文件内容。
        """
        cache_key = "memory_md"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        lines = ["# 长期记忆\n"]

        # 获取重要记忆（重要性 ≥ 0.8）
        important_memories = self.manager.get_important_memories(min_importance=0.8)

        if important_memories:
            lines.append("## 重要记忆（重要性 ≥ 0.8）")
            for i, memory in enumerate(important_memories, 1):
                lines.append(f"{i}. [{memory['category']}] {memory['content']}")
                lines.append(
                    f"   重要性: {memory['importance']:.2f} | 创建时间: {memory['created_at'][:10]} | 访问次数: {memory['access_count']}"
                )
                lines.append("")
        else:
            lines.append("## 重要记忆")
            lines.append("暂无重要记忆")
            lines.append("")

        # 获取最近7天的记忆
        recent_memories = self.manager.get_recent_memories(days=7)

        if recent_memories:
            lines.append("## 近期记忆（最近7天）")
            for memory in recent_memories[:10]:  # 最多显示10条
                lines.append(f"- [{memory['category']}] {memory['content'][:50]}...")
        else:
            lines.append("## 近期记忆")
            lines.append("暂无近期记忆")

        # 添加记忆统计
        stats = self.manager.get_stats()
        sqlite_stats = stats.get("sqlite", {})

        lines.append("\n## 记忆统计")
        lines.append(f"- 总记忆数: {sqlite_stats.get('total', 0)}")
        lines.append(f"- 重要记忆: {sqlite_stats.get('important', 0)}")
        lines.append(f"- 归档记忆: {sqlite_stats.get('archived', 0)}")
        lines.append(f"- 平均重要性: {sqlite_stats.get('avg_importance', 0):.2f}")
        lines.append(f"- 总访问次数: {sqlite_stats.get('total_accesses', 0)}")

        if sqlite_stats.get("latest_accessed"):
            lines.append(f"- 最近访问: {sqlite_stats['latest_accessed'][:19]}")

        content = "\n".join(lines)

        # 写入文件
        self._write_file(self.memory_dir / "MEMORY.md", content)

        # 更新缓存
        self._update_cache(cache_key, content)

        logger.debug("MEMORY.md generated")
        return content

    def generate_daily_md(self, date: datetime | None = None) -> str:
        """生成每日笔记MD文件.

        Args:
            date: 日期，如果为None则使用今天。

        Returns:
            MD文件内容。
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y-%m-%d")
        cache_key = f"daily_{date_str}"

        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        # 获取当天的记忆
        memories = self.manager.search_memories(
            query=None,
            category=None,
            include_archived=False,
            limit=100,
        )

        # 过滤当天的记忆（根据创建时间）
        daily_memories = []
        for memory in memories:
            created_at = memory.get("created_at")
            if created_at and created_at.startswith(date_str):
                daily_memories.append(memory)

        lines = [f"# {date_str}\n"]

        if daily_memories:
            lines.append("## 记忆条目")

            # 按时间排序
            daily_memories.sort(key=lambda x: x.get("created_at", ""))

            for i, memory in enumerate(daily_memories, 1):
                created_time = (
                    memory.get("created_at", "")[11:16] if memory.get("created_at") else "未知时间"
                )
                lines.append(f"{i}. **{created_time}** [{memory['category']}] {memory['content']}")

                # 添加元数据（如果有）
                metadata = memory.get("metadata", {})
                if metadata:
                    metadata_str = ", ".join([f"{k}: {v}" for k, v in metadata.items()])
                    lines.append(f"   元数据: {metadata_str}")

                lines.append("")
        else:
            lines.append("## 记忆条目")
            lines.append("今日暂无记忆")
            lines.append("")

        # 添加今日统计
        lines.append("## 今日统计")
        lines.append(f"- 新增记忆: {len(daily_memories)}")

        # 计算今日访问次数
        today_accesses = 0
        for memory in daily_memories:
            today_accesses += memory.get("access_count", 0)

        lines.append(f"- 访问次数: {today_accesses}")

        # 获取重要记忆数量
        important_today = len([m for m in daily_memories if m.get("importance", 0) >= 0.8])
        lines.append(f"- 重要记忆: {important_today}")

        content = "\n".join(lines)

        # 写入文件
        file_path = self.daily_dir / f"{date_str}.md"
        self._write_file(file_path, content)

        # 更新缓存
        self._update_cache(cache_key, content)

        logger.debug(f"Daily MD generated for {date_str}")
        return content

    def generate_category_md(self, category_name: str) -> str:
        """生成分类视图MD文件.

        Args:
            category_name: 分类名称。

        Returns:
            MD文件内容。
        """
        cache_key = f"category_{category_name}"

        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        # 获取该分类的记忆
        memories = self.manager.search_memories(
            query=None,
            category=category_name,
            include_archived=False,
            limit=100,
        )

        lines = [f"# {category_name} 相关记忆\n"]

        if memories:
            # 按重要性排序
            memories.sort(key=lambda x: x.get("importance", 0), reverse=True)

            lines.append("## 记忆列表")

            for i, memory in enumerate(memories, 1):
                lines.append(f"{i}. {memory['content']}")
                lines.append(
                    f"   重要性: {memory['importance']:.2f} | 创建时间: {memory['created_at'][:10]} | 访问次数: {memory['access_count']}"
                )

                # 添加标签（如果有）
                tags = memory.get("tags", [])
                if tags:
                    lines.append(f"   标签: {', '.join(tags)}")

                lines.append("")
        else:
            lines.append("## 记忆列表")
            lines.append(f"暂无 {category_name} 相关记忆")
            lines.append("")

        # 添加分类统计
        total_importance = sum(m.get("importance", 0) for m in memories)
        avg_importance = total_importance / len(memories) if memories else 0

        lines.append("## 分类统计")
        lines.append(f"- 记忆数量: {len(memories)}")
        lines.append(f"- 平均重要性: {avg_importance:.2f}")
        lines.append(f"- 总访问次数: {sum(m.get('access_count', 0) for m in memories)}")

        # 最近更新
        if memories:
            latest = max(memories, key=lambda x: x.get("created_at", ""))
            lines.append(f"- 最近更新: {latest['created_at'][:19]}")

        content = "\n".join(lines)

        # 写入文件
        file_path = self.categories_dir / f"{category_name}.md"
        self._write_file(file_path, content)

        # 更新缓存
        self._update_cache(cache_key, content)

        logger.debug(f"Category MD generated for {category_name}")
        return content

    def generate_user_profile(self) -> str:
        """生成用户档案MD文件.

        Returns:
            MD文件内容。
        """
        cache_key = "user_profile_md"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        lines = ["# 用户档案\n"]

        # 获取个人信息（personal类别，重要性≥0.7）
        personal_memories = self.manager.search_memories(
            category="personal",
            min_importance=0.7,
            include_archived=False,
            limit=50,
        )

        if personal_memories:
            lines.append("## 基本信息")
            for memory in personal_memories:
                lines.append(f"- {memory['content']}")
            lines.append("")
        else:
            lines.append("## 基本信息")
            lines.append("暂无个人信息")
            lines.append("")

        # 获取偏好信息（preference类别）
        preference_memories = self.manager.search_memories(
            category="preference",
            include_archived=False,
            limit=30,
        )

        if preference_memories:
            lines.append("## 偏好")
            for memory in preference_memories:
                lines.append(f"- {memory['content']}")
            lines.append("")
        else:
            lines.append("## 偏好")
            lines.append("暂无偏好信息")
            lines.append("")

        # 获取联系方式（contact类别）
        contact_memories = self.manager.search_memories(
            category="contact",
            min_importance=0.8,
            include_archived=False,
            limit=20,
        )

        if contact_memories:
            lines.append("## 联系方式")
            for memory in contact_memories:
                lines.append(f"- {memory['content']}")
            lines.append("")

        # 添加统计信息
        stats = self.manager.get_stats()
        sqlite_stats = stats.get("sqlite", {})

        lines.append("## 记忆统计")
        lines.append(f"- 总记忆数: {sqlite_stats.get('total', 0)}")
        lines.append(f"- 个人信息: {len(personal_memories)}")
        lines.append(f"- 偏好设置: {len(preference_memories)}")

        if sqlite_stats.get("latest_accessed"):
            lines.append(f"- 最近活跃: {sqlite_stats['latest_accessed'][:19]}")

        content = "\n".join(lines)

        self._write_file(self.memory_dir / "USER_PROFILE.md", content)
        self._update_cache(cache_key, content)
        logger.debug("USER_PROFILE.md generated")
        return content

    def generate_all_category_mds(self) -> dict[str, str]:
        """生成所有分类的MD文件.

        Returns:
            字典：分类名称 -> MD内容。
        """
        # 获取所有分类
        categories = self.manager.get_categories()

        results = {}
        for category in categories:
            category_name = category.get("name")
            if category_name:
                content = self.generate_category_md(category_name)
                results[category_name] = content

        # 如果没有分类，生成默认分类
        if not results:
            default_categories = ["personal", "work", "preference", "contact", "goal", "schedule"]
            for cat in default_categories:
                content = self.generate_category_md(cat)
                results[cat] = content

        logger.info(f"Generated {len(results)} category MD files")
        return results

    def cleanup_old_daily_files(self, keep_days: int = 30) -> int:
        """清理旧的每日笔记文件.

        策略：
        - 保留最近 keep_days 天的文件
        - 保留每月1日的文件（历史快照）
        - 删除其他超过 keep_days 天的文件

        Args:
            keep_days: 保留最近天数。

        Returns:
            删除的文件数量。
        """
        from datetime import datetime, timedelta

        if not self.daily_dir.exists():
            return 0

        today = datetime.now()
        cutoff_date = today - timedelta(days=keep_days)
        deleted_count = 0

        for file_path in self.daily_dir.glob("*.md"):
            try:
                date_str = file_path.stem
                file_date = datetime.strptime(date_str, "%Y-%m-%d")

                # 检查是否是每月1日（保留历史快照）
                is_first_day = file_date.day == 1

                # 检查是否在保留期内
                is_recent = file_date >= cutoff_date

                if not is_recent and not is_first_day:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old daily file: {date_str}")
            except (ValueError, Exception) as e:
                logger.warning(f"Failed to process daily file {file_path}: {e}")

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old daily files")

        return deleted_count

    def generate_recent_daily_mds(self, days: int = 7) -> dict[str, str]:
        """生成最近几天的每日笔记.

        Args:
            days: 最近天数。

        Returns:
            字典：日期 -> MD内容。
        """
        results = {}

        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")

            content = self.generate_daily_md(date)
            results[date_str] = content

        logger.info(f"Generated {len(results)} daily MD files")
        return results

    def update_all_md_files(self) -> dict[str, Any]:
        """更新所有MD文件.

        Returns:
            更新统计。
        """
        start_time = datetime.now()

        # 生成各种MD文件
        memory_md = self.generate_memory_md()
        user_profile_md = self.generate_user_profile()
        category_mds = self.generate_all_category_mds()
        daily_mds = self.generate_recent_daily_mds(days=7)

        # 清理旧的每日笔记
        deleted_daily = self.cleanup_old_daily_files(keep_days=30)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        stats = {
            "memory_md_size": len(memory_md),
            "user_profile_md_size": len(user_profile_md),
            "category_md_count": len(category_mds),
            "daily_md_count": len(daily_mds),
            "deleted_daily_count": deleted_daily,
            "total_files": 2 + len(category_mds) + len(daily_mds),
            "duration_seconds": round(duration, 2),
            "timestamp": end_time.isoformat(),
        }

        logger.info(f"All MD files updated: {stats}")
        return stats

    def get_md_file_paths(self) -> dict[str, Any]:
        """获取所有MD文件路径.

        Returns:
            字典：文件类型 -> 路径/目录/子字典。
        """
        paths: dict[str, Any] = {
            "memory_md": self.memory_dir / "MEMORY.md",
            "daily_dir": self.daily_dir,
            "categories_dir": self.categories_dir,
        }

        # 添加具体的每日文件
        daily_files = {}
        for file in self.daily_dir.glob("*.md"):
            daily_files[file.stem] = file

        # 添加具体的分类文件
        category_files = {}
        for file in self.categories_dir.glob("*.md"):
            category_files[file.stem] = file

        paths["daily_files"] = daily_files
        paths["category_files"] = category_files

        return paths

    def _write_file(self, file_path: Path, content: str) -> None:
        """写入文件.

        Args:
            file_path: 文件路径。
            content: 文件内容。
        """
        try:
            file_path.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")

    def _get_from_cache(self, key: str) -> str | None:
        """从缓存获取数据.

        Args:
            key: 缓存键。

        Returns:
            缓存数据，如果未命中或过期返回None。
        """
        if key in self.cache:
            cached_data = self.cache[key]
            cached_time = cached_data.get("timestamp")

            if cached_time:
                cache_age = (datetime.now() - cached_time).total_seconds()
                if cache_age < self.cache_ttl:
                    return cached_data.get("content")

        return None

    def _update_cache(self, key: str, content: str) -> None:
        """更新缓存.

        Args:
            key: 缓存键。
            content: 缓存内容。
        """
        self.cache[key] = {
            "content": content,
            "timestamp": datetime.now(),
        }

        # 清理过期缓存
        self._clean_cache()

    def _clean_cache(self) -> None:
        """清理过期缓存."""
        current_time = datetime.now()
        keys_to_remove = []

        for key, data in self.cache.items():
            cached_time = data.get("timestamp")
            if cached_time:
                cache_age = (current_time - cached_time).total_seconds()
                if cache_age >= self.cache_ttl:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.cache[key]

        if keys_to_remove:
            logger.debug(f"Cleaned {len(keys_to_remove)} expired cache entries")

    def invalidate_cache(self, key: str | None = None) -> None:
        """使缓存失效.

        Args:
            key: 缓存键，如果为None则清除所有缓存。
        """
        if key is None:
            self.cache.clear()
            logger.debug("All cache invalidated")
        elif key in self.cache:
            del self.cache[key]
            logger.debug(f"Cache invalidated for key: {key}")

    def close(self) -> None:
        """关闭MD文件生成器."""
        self.manager.close()
        logger.info("MDFileGenerator closed")

    def __enter__(self):
        """上下文管理器入口."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口."""
        self.close()


class MDSystem:
    """完整的MD文件系统.

    整合MemoryManager和MDFileGenerator，
    提供完整的MD文件生成和管理功能。
    """

    def __init__(self, workspace: Path) -> None:
        """初始化MD系统.

        Args:
            workspace: 工作目录路径。
        """
        self.workspace = workspace
        self.manager = MemoryManager(workspace)
        self.generator = MDFileGenerator(workspace)

        logger.info(f"MDSystem initialized at {self.workspace}")

    def remember(
        self,
        content: str,
        category: str | None = None,
        importance: float | None = None,
        source: str = "manual",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """保存记忆并更新相关MD文件.

        Args:
            content: 记忆内容。
            category: 分类标签。
            importance: 重要性评分。
            source: 来源。
            tags: 标签列表。
            metadata: 元数据。

        Returns:
            记忆字典，如果失败返回None。
        """
        # 保存记忆
        memory = self.manager.remember(
            content=content,
            category=category,
            importance=importance,
            source=source,
            tags=tags,
            metadata=metadata,
        )

        # 使相关缓存失效
        self.generator.invalidate_cache("memory_md")
        self.generator.invalidate_cache("user_profile_md")

        if category:
            self.generator.invalidate_cache(f"category_{category}")

        # 更新今日的每日笔记
        self.generator.invalidate_cache(f"daily_{datetime.now().strftime('%Y-%m-%d')}")

        return memory

    def update_all_md_files(self) -> dict[str, Any]:
        """更新所有MD文件.

        Returns:
            更新统计。
        """
        return self.generator.update_all_md_files()

    def generate_user_profile(self) -> str:
        """生成用户档案MD文件.

        Returns:
            MD文件内容。
        """
        return self.generator.generate_user_profile()

    def cleanup_old_daily_files(self, keep_days: int = 30) -> int:
        """清理旧的每日笔记文件.

        Args:
            keep_days: 保留最近天数。

        Returns:
            删除的文件数量。
        """
        return self.generator.cleanup_old_daily_files(keep_days)

    def get_stats(self) -> dict[str, Any]:
        """获取系统统计信息.

        Returns:
            统计字典。
        """
        return self.manager.get_stats()

    def close(self) -> None:
        """关闭MD系统."""
        self.generator.close()
        self.manager.close()
        logger.info("MDSystem closed")

    def __enter__(self):
        """上下文管理器入口."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口."""
        self.close()
