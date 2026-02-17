"""测试MD文件生成器功能.

验证MDFileGenerator的核心功能：
1. MEMORY.md生成
2. 每日笔记生成
3. 分类视图生成
4. 缓存机制
"""

import tempfile
from datetime import datetime
from pathlib import Path

from finchbot.memory.md_generator import MDFileGenerator


def test_memory_md_generation():
    """测试MEMORY.md生成."""
    print("\n" + "=" * 60)
    print("测试 1: MEMORY.md生成")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)
        generator = MDFileGenerator(workspace)

        # 添加测试记忆
        manager = generator.manager
        manager.remember("重要记忆1", "personal", 0.9, "test")
        manager.remember("普通记忆1", "work", 0.6, "test")
        manager.remember("重要记忆2", "personal", 0.85, "test")

        # 生成MEMORY.md
        content = generator.generate_memory_md()

        assert content is not None
        assert "# 长期记忆" in content
        assert "重要记忆" in content
        assert "记忆统计" in content

        # 检查文件是否创建
        memory_md_path = workspace / "memory" / "MEMORY.md"
        assert memory_md_path.exists()

        print("✓ MEMORY.md生成成功")
        print(f"  文件大小: {len(content)} 字符")
        print(f"  文件路径: {memory_md_path}")

        generator.close()
        print("\n✅ MEMORY.md生成测试通过!")


def test_daily_md_generation():
    """测试每日笔记生成."""
    print("\n" + "=" * 60)
    print("测试 2: 每日笔记生成")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)
        generator = MDFileGenerator(workspace)

        # 添加测试记忆
        manager = generator.manager

        # 添加今天的记忆
        today = datetime.now()
        manager.remember("今日记忆1", "personal", 0.7, "test")
        manager.remember("今日记忆2", "work", 0.8, "test")

        # 生成今日笔记
        content = generator.generate_daily_md(today)

        assert content is not None
        today_str = today.strftime("%Y-%m-%d")
        assert f"# {today_str}" in content
        assert "记忆条目" in content
        assert "今日统计" in content

        # 检查文件是否创建
        daily_dir = workspace / "memory" / "daily"
        daily_file = daily_dir / f"{today_str}.md"
        assert daily_file.exists()

        print("✓ 每日笔记生成成功")
        print(f"  日期: {today_str}")
        print(f"  文件路径: {daily_file}")

        # 测试生成最近7天的笔记
        recent_mds = generator.generate_recent_daily_mds(days=3)
        assert len(recent_mds) == 3

        print(f"✓ 最近3天笔记生成成功: {len(recent_mds)} 个文件")

        generator.close()
        print("\n✅ 每日笔记生成测试通过!")


def test_category_md_generation():
    """测试分类视图生成."""
    print("\n" + "=" * 60)
    print("测试 3: 分类视图生成")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)
        generator = MDFileGenerator(workspace)

        # 添加测试记忆
        manager = generator.manager

        # 添加不同分类的记忆
        test_data = [
            ("个人记忆1", "personal", 0.8),
            ("个人记忆2", "personal", 0.7),
            ("工作记忆1", "work", 0.6),
            ("工作记忆2", "work", 0.9),
            ("偏好记忆", "preference", 0.5),
        ]

        for content, category, importance in test_data:
            manager.remember(content, category, importance, "test")

        # 生成个人分类视图
        personal_content = generator.generate_category_md("personal")

        assert personal_content is not None
        assert "# personal 相关记忆" in personal_content
        assert "个人记忆1" in personal_content
        assert "个人记忆2" in personal_content
        assert "分类统计" in personal_content

        # 检查文件是否创建
        categories_dir = workspace / "memory" / "categories"
        personal_file = categories_dir / "personal.md"
        assert personal_file.exists()

        print("✓ 分类视图生成成功")
        print("  分类: personal")
        print(f"  文件路径: {personal_file}")

        # 测试生成所有分类视图
        all_categories = generator.generate_all_category_mds()
        assert len(all_categories) >= 3  # personal, work, preference

        print(f"✓ 所有分类视图生成成功: {len(all_categories)} 个文件")

        generator.close()
        print("\n✅ 分类视图生成测试通过!")


def test_cache_mechanism():
    """测试缓存机制."""
    print("\n" + "=" * 60)
    print("测试 4: 缓存机制")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)
        generator = MDFileGenerator(workspace)

        # 第一次生成MEMORY.md（应该未命中缓存）
        start_time = datetime.now()
        content1 = generator.generate_memory_md()
        first_duration = (datetime.now() - start_time).total_seconds()

        print(f"第一次生成耗时: {first_duration:.3f} 秒")

        # 第二次生成MEMORY.md（应该命中缓存）
        start_time = datetime.now()
        content2 = generator.generate_memory_md()
        second_duration = (datetime.now() - start_time).total_seconds()

        print(f"第二次生成耗时: {second_duration:.3f} 秒")

        # 缓存应该使第二次更快
        assert second_duration < first_duration

        # 内容应该相同
        assert content1 == content2

        print("✓ 缓存机制验证成功")
        print(f"  第一次耗时: {first_duration:.3f} 秒")
        print(f"  第二次耗时: {second_duration:.3f} 秒")
        print(f"  加速比: {first_duration/second_duration:.1f}x")

        # 测试缓存失效
        generator.invalidate_cache("memory_md")

        # 第三次生成（缓存失效后应该重新生成）
        start_time = datetime.now()
        content3 = generator.generate_memory_md()
        third_duration = (datetime.now() - start_time).total_seconds()

        print(f"缓存失效后生成耗时: {third_duration:.3f} 秒")

        # 内容应该仍然相同
        assert content3 == content1

        print("✓ 缓存失效机制验证成功")

        generator.close()
        print("\n✅ 缓存机制测试通过!")


def test_update_all_md_files():
    """测试更新所有MD文件."""
    print("\n" + "=" * 60)
    print("测试 5: 更新所有MD文件")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)
        generator = MDFileGenerator(workspace)

        # 添加测试记忆
        manager = generator.manager

        # 添加各种记忆
        test_data = [
            ("记忆1", "personal", 0.8),
            ("记忆2", "work", 0.7),
            ("记忆3", "preference", 0.6),
            ("记忆4", "contact", 0.9),
            ("记忆5", "goal", 0.85),
        ]

        for content, category, importance in test_data:
            manager.remember(content, category, importance, "test")

        # 更新所有MD文件
        stats = generator.update_all_md_files()

        assert stats is not None
        assert "memory_md_size" in stats
        assert "category_md_count" in stats
        assert "daily_md_count" in stats
        assert "total_files" in stats
        assert "duration_seconds" in stats

        print("✓ 所有MD文件更新成功")
        print("  统计信息:")
        print(f"    MEMORY.md大小: {stats['memory_md_size']} 字符")
        print(f"    分类文件数: {stats['category_md_count']}")
        print(f"    每日文件数: {stats['daily_md_count']}")
        print(f"    总文件数: {stats['total_files']}")
        print(f"    耗时: {stats['duration_seconds']} 秒")

        # 检查所有文件是否创建
        memory_md_path = workspace / "memory" / "MEMORY.md"
        assert memory_md_path.exists()

        daily_dir = workspace / "memory" / "daily"
        assert daily_dir.exists()

        categories_dir = workspace / "memory" / "categories"
        assert categories_dir.exists()

        # 检查每日文件数量
        daily_files = list(daily_dir.glob("*.md"))
        assert len(daily_files) >= 1

        # 检查分类文件数量
        category_files = list(categories_dir.glob("*.md"))
        assert len(category_files) >= 3

        print("✓ 文件系统验证成功")
        print(f"  每日文件数: {len(daily_files)}")
        print(f"  分类文件数: {len(category_files)}")

        generator.close()
        print("\n✅ 更新所有MD文件测试通过!")


def test_md_system_integration():
    """测试MD系统集成."""
    print("\n" + "=" * 60)
    print("测试 6: MD系统集成")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)

        # 创建MD系统
        from finchbot.memory.md_generator import MDSystem
        md_system = MDSystem(workspace)

        # 通过系统保存记忆
        memory = md_system.remember(
            content="集成测试记忆",
            category="personal",
            importance=0.8,
            source="test",
        )

        assert memory is not None
        assert memory["content"] == "集成测试记忆"

        print(f"✓ 记忆保存成功: {memory['id'][:8]}...")

        # 更新所有MD文件
        stats = md_system.update_all_md_files()

        assert stats is not None
        assert stats["total_files"] >= 1

        print(f"✓ MD文件更新成功: {stats['total_files']} 个文件")

        # 获取统计信息
        system_stats = md_system.get_stats()

        assert system_stats is not None
        assert "sqlite" in system_stats

        print("✓ 系统统计获取成功")

        md_system.close()
        print("\n✅ MD系统集成测试通过!")


if __name__ == "__main__":
    """运行所有测试."""
    test_memory_md_generation()
    test_daily_md_generation()
    test_category_md_generation()
    test_cache_mechanism()
    test_update_all_md_files()
    test_md_system_integration()

    print("\n" + "=" * 60)
    print("所有MD文件生成器测试通过! ✅")
    print("=" * 60)
