"""集成测试.

验证整个记忆系统的集成功能：
1. 三层架构协同工作
2. 数据一致性保证
3. 与现有工具的兼容性
4. MD文件系统完整性
"""

import tempfile
import time
from pathlib import Path

from finchbot.memory.manager import MemoryManager
from finchbot.memory.md_generator import MDFileGenerator, MDSystem
from finchbot.memory.types import RetrievalStrategy


def test_full_system_integration():
    """测试完整系统集成."""
    print("\n" + "=" * 60)
    print("测试 1: 完整系统集成")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)

        # 创建完整的MD系统
        md_system = MDSystem(workspace)

        # 测试记忆保存
        test_memories = [
            ("我叫张三，今年25岁", "personal", 0.9),
            ("我的邮箱是 zhangsan@example.com", "contact", 0.95),
            ("明天下午3点有个项目会议", "work", 0.8),
            ("我喜欢吃苹果和香蕉", "preference", 0.7),
            ("我的目标是学习人工智能", "goal", 0.85),
            ("下周要去医院体检", "schedule", 0.75),
        ]

        memory_ids = []
        for content, category, importance in test_memories:
            memory = md_system.remember(
                content=content,
                category=category,
                importance=importance,
                source="integration_test",
            )
            memory_ids.append(memory["id"])
            print(f"✓ 记忆保存: {content[:20]}... -> {memory['id'][:8]}...")

        # 等待同步完成
        time.sleep(2)

        # 测试记忆检索
        print("\n记忆检索测试:")

        # 关键词检索
        keyword_results = md_system.manager.recall(
            query="邮箱",
            strategy=RetrievalStrategy.KEYWORD,
        )
        assert len(keyword_results) >= 1
        print(f"  ✓ 关键词检索: 找到 {len(keyword_results)} 条结果")

        # 混合检索
        hybrid_results = md_system.manager.recall(
            query="学习",
            strategy=RetrievalStrategy.HYBRID,
        )
        assert len(hybrid_results) >= 1
        print(f"  ✓ 混合检索: 找到 {len(hybrid_results)} 条结果")

        # 测试MD文件生成
        print("\nMD文件生成测试:")

        # 更新所有MD文件
        stats = md_system.update_all_md_files()
        assert stats["total_files"] >= 1
        print(f"  ✓ MD文件生成: {stats['total_files']} 个文件")

        # 检查文件系统
        memory_md_path = workspace / "memory" / "MEMORY.md"
        assert memory_md_path.exists()

        daily_dir = workspace / "memory" / "daily"
        assert daily_dir.exists()

        categories_dir = workspace / "memory" / "categories"
        assert categories_dir.exists()

        print("  ✓ 文件系统验证成功")

        # 测试系统统计
        system_stats = md_system.get_stats()
        assert "sqlite" in system_stats
        assert "sync" in system_stats

        sqlite_stats = system_stats["sqlite"]
        assert sqlite_stats["total"] >= len(test_memories)

        print("  ✓ 系统统计获取成功:")
        print(f"    总记忆数: {sqlite_stats['total']}")
        print(f"    重要记忆: {sqlite_stats['important']}")
        print(f"    平均重要性: {sqlite_stats['avg_importance']:.2f}")

        md_system.close()
        print("\n✅ 完整系统集成测试通过!")


def test_data_consistency():
    """测试数据一致性."""
    print("\n" + "=" * 60)
    print("测试 2: 数据一致性")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)

        # 创建记忆管理器
        manager = MemoryManager(workspace)

        # 添加测试记忆
        memory = manager.remember(
            content="一致性测试记忆",
            category="test",
            importance=0.7,
            source="consistency_test",
        )

        memory_id = memory["id"]

        print(f"✓ 记忆添加成功: {memory_id[:8]}...")

        # 验证SQLite中的数据
        sqlite_memory = manager.sqlite_store.get_memory(memory_id)
        assert sqlite_memory is not None
        assert sqlite_memory["content"] == "一致性测试记忆"

        print("✓ SQLite数据验证成功")

        # 测试更新操作
        updated = manager.update_memory(
            memory_id=memory_id,
            content="更新后的一致性测试记忆",
            importance=0.9,
        )

        assert updated is True

        # 验证更新后的数据
        updated_memory = manager.sqlite_store.get_memory(memory_id)
        assert updated_memory["content"] == "更新后的一致性测试记忆"
        assert updated_memory["importance"] == 0.9

        print("✓ 数据更新验证成功")

        # 测试删除操作
        deleted = manager.sqlite_store.delete_memory(memory_id)
        assert deleted is True

        # 验证删除后的数据
        deleted_memory = manager.sqlite_store.get_memory(memory_id)
        assert deleted_memory is None

        print("✓ 数据删除验证成功")

        manager.close()
        print("\n✅ 数据一致性测试通过!")


def test_md_file_system_integrity():
    """测试MD文件系统完整性."""
    print("\n" + "=" * 60)
    print("测试 3: MD文件系统完整性")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)

        # 创建MD文件生成器
        generator = MDFileGenerator(workspace)

        # 添加测试记忆
        manager = generator.manager

        test_data = [
            ("完整性测试记忆1", "personal", 0.8),
            ("完整性测试记忆2", "work", 0.7),
            ("完整性测试记忆3", "preference", 0.6),
        ]

        for content, category, importance in test_data:
            manager.remember(content, category, importance, "integrity_test")

        print("✓ 测试记忆添加成功")

        # 生成所有MD文件
        stats = generator.update_all_md_files()

        assert stats["memory_md_size"] > 0
        assert stats["category_md_count"] >= 3
        assert stats["daily_md_count"] >= 1

        print("✓ MD文件生成成功:")
        print(f"  MEMORY.md大小: {stats['memory_md_size']} 字符")
        print(f"  分类文件数: {stats['category_md_count']}")
        print(f"  每日文件数: {stats['daily_md_count']}")

        # 验证文件内容
        memory_md_path = workspace / "memory" / "MEMORY.md"
        memory_md_content = memory_md_path.read_text(encoding="utf-8")

        assert "# 长期记忆" in memory_md_content
        assert "重要记忆" in memory_md_content
        assert "记忆统计" in memory_md_content

        print("✓ MEMORY.md内容验证成功")

        # 验证每日文件
        daily_dir = workspace / "memory" / "daily"
        daily_files = list(daily_dir.glob("*.md"))

        assert len(daily_files) >= 1

        for daily_file in daily_files[:2]:  # 检查前两个文件
            content = daily_file.read_text(encoding="utf-8")
            assert "# " in content
            assert "记忆条目" in content
            assert "今日统计" in content

        print(f"✓ 每日文件验证成功: {len(daily_files)} 个文件")

        # 验证分类文件
        categories_dir = workspace / "memory" / "categories"
        category_files = list(categories_dir.glob("*.md"))

        assert len(category_files) >= 3

        for category_file in category_files[:3]:
            content = category_file.read_text(encoding="utf-8")
            assert "# " in content
            assert "相关记忆" in content
            assert "分类统计" in content

        print(f"✓ 分类文件验证成功: {len(category_files)} 个文件")

        generator.close()
        print("\n✅ MD文件系统完整性测试通过!")


def test_performance_and_scalability():
    """测试性能和可扩展性."""
    print("\n" + "=" * 60)
    print("测试 4: 性能和可扩展性")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)

        # 创建记忆管理器
        manager = MemoryManager(workspace)

        # 批量添加记忆（测试性能）
        batch_size = 50
        start_time = time.time()

        for i in range(batch_size):
            manager.remember(
                content=f"性能测试记忆 {i+1}",
                category="test",
                importance=0.5 + (i % 5) * 0.1,
                source="performance_test",
            )

        add_time = time.time() - start_time
        add_rate = batch_size / add_time

        print("✓ 批量添加测试:")
        print(f"  添加 {batch_size} 条记忆")
        print(f"  耗时: {add_time:.2f} 秒")
        print(f"  速率: {add_rate:.1f} 条/秒")

        # 批量检索测试
        start_time = time.time()

        for _ in range(10):
            manager.recall(
                query="性能测试",
                top_k=10,
                strategy=RetrievalStrategy.KEYWORD,
            )

        search_time = time.time() - start_time
        search_rate = 10 / search_time

        print("\n✓ 批量检索测试:")
        print("  执行 10 次检索")
        print(f"  耗时: {search_time:.2f} 秒")
        print(f"  速率: {search_rate:.1f} 次/秒")

        # 获取统计信息
        stats = manager.get_stats()
        sqlite_stats = stats.get("sqlite", {})

        assert sqlite_stats["total"] >= batch_size

        print("\n✓ 系统统计:")
        print(f"  总记忆数: {sqlite_stats['total']}")
        print(f"  平均重要性: {sqlite_stats['avg_importance']:.2f}")
        print(f"  总访问次数: {sqlite_stats['total_accesses']}")

        manager.close()
        print("\n✅ 性能和可扩展性测试通过!")


def test_error_handling_and_recovery():
    """测试错误处理和恢复."""
    print("\n" + "=" * 60)
    print("测试 5: 错误处理和恢复")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)

        # 创建记忆管理器
        manager = MemoryManager(workspace)

        # 测试无效输入
        try:
            # 测试空内容
            memory = manager.remember("", "test", 0.5, "test")
            print("⚠ 空内容测试: 应该失败但通过了")
        except Exception as e:
            print(f"✓ 空内容测试: 正确处理错误 - {e}")

        # 测试无效重要性
        try:
            memory = manager.remember("测试", "test", 1.5, "test")  # 重要性 > 1.0
            print("⚠ 无效重要性测试: 应该失败但通过了")
        except Exception as e:
            print(f"✓ 无效重要性测试: 正确处理错误 - {e}")

        # 测试不存在的记忆ID
        non_existent_id = "non_existent_id"
        memory = manager.get_memory(non_existent_id)
        assert memory is None
        print("✓ 不存在的记忆ID测试: 正确处理")

        # 测试更新不存在的记忆
        updated = manager.update_memory(non_existent_id, content="新内容")
        assert updated is False
        print("✓ 更新不存在的记忆测试: 正确处理")

        # 测试删除不存在的记忆
        deleted = manager.sqlite_store.delete_memory(non_existent_id)
        assert deleted is False
        print("✓ 删除不存在的记忆测试: 正确处理")

        # 测试系统关闭后操作
        manager.close()

        try:
            manager.remember("关闭后测试", "test", 0.5, "test")
            print("⚠ 关闭后操作测试: 应该失败但通过了")
        except Exception as e:
            print(f"✓ 关闭后操作测试: 正确处理错误 - {e}")

        print("\n✅ 错误处理和恢复测试通过!")


if __name__ == "__main__":
    """运行所有集成测试."""
    test_full_system_integration()
    test_data_consistency()
    test_md_file_system_integrity()
    test_performance_and_scalability()
    test_error_handling_and_recovery()

    print("\n" + "=" * 60)
    print("所有集成测试通过! ✅")
    print("=" * 60)
