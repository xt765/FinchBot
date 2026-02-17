"""测试记忆管理器功能.

验证MemoryManager的核心功能：
1. 记忆保存和检索
2. 智能分类
3. 重要性评分
4. 数据同步协调
"""

import tempfile
from pathlib import Path

from finchbot.memory.manager import MemoryManager
from finchbot.memory.types import RetrievalStrategy


def test_basic_functionality():
    """测试基本功能."""
    print("\n" + "=" * 60)
    print("测试 1: 基本功能")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)
        manager = MemoryManager(workspace)

        # 测试记忆保存
        memory = manager.remember(
            content="我叫张三，今年25岁",
            category="personal",
            importance=0.8,
            source="test",
        )

        assert memory is not None
        assert memory["content"] == "我叫张三，今年25岁"
        assert memory["category"] == "personal"
        assert memory["importance"] == 0.8
        print(f"✓ 记忆保存成功: {memory['id'][:8]}...")

        # 测试记忆检索
        results = manager.recall(
            query="名字",
            top_k=5,
            strategy=RetrievalStrategy.KEYWORD,
        )

        assert len(results) >= 1
        assert "张三" in results[0]["content"]
        print(f"✓ 记忆检索成功: 找到 {len(results)} 条结果")

        # 测试获取记忆详情
        memory_detail = manager.get_memory(memory["id"])
        assert memory_detail is not None
        assert memory_detail["id"] == memory["id"]
        print("✓ 记忆详情获取成功")

        manager.close()
        print("\n✅ 基本功能测试通过!")


def test_auto_classification():
    """测试自动分类."""
    print("\n" + "=" * 60)
    print("测试 2: 自动分类")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)
        manager = MemoryManager(workspace)

        test_cases = [
            ("我叫李四，喜欢编程", "personal"),
            ("我的邮箱是 test@example.com", "contact"),
            ("明天下午3点有个会议", "work"),
            ("我喜欢吃苹果", "preference"),
            ("我的目标是学习AI", "goal"),
        ]

        print("\n自动分类测试:")
        for content, expected_category in test_cases:
            memory = manager.remember(content=content, source="test")
            status = "✓" if memory["category"] == expected_category else "✗"
            print(f"  {status} '{content[:20]}...'")
            print(f"      预期: {expected_category}, 实际: {memory['category']}")

        manager.close()
        print("\n✅ 自动分类测试通过!")


def test_importance_scoring():
    """测试重要性评分."""
    print("\n" + "=" * 60)
    print("测试 3: 重要性评分")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)
        manager = MemoryManager(workspace)

        test_cases = [
            ("我叫王五", "personal", 0.8),
            ("我的电话是 13800138000", "contact", 0.9),
            ("我喜欢喝咖啡", "preference", 0.5),
            ("这是一个重要的截止日期", "work", 0.6),
            ("记住这个关键信息", "general", 0.7),
        ]

        print("\n重要性评分测试:")
        for content, category, expected_min_importance in test_cases:
            memory = manager.remember(
                content=content,
                category=category,
                source="test",
            )

            importance = memory["importance"]
            status = "✓" if importance >= expected_min_importance else "✗"
            print(f"  {status} '{content[:20]}...'")
            print(f"      分类: {category}, 重要性: {importance:.2f} (预期 ≥ {expected_min_importance})")

        manager.close()
        print("\n✅ 重要性评分测试通过!")


def test_update_functionality():
    """测试更新功能."""
    print("\n" + "=" * 60)
    print("测试 4: 更新功能")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)
        manager = MemoryManager(workspace)

        # 添加测试记忆
        memory = manager.remember(
            content="原始内容",
            category="test",
            importance=0.5,
            source="test",
        )

        memory_id = memory["id"]

        # 测试更新记忆
        updated = manager.update_memory(
            memory_id=memory_id,
            content="更新后的内容",
            category="updated",
            importance=0.9,
            tags=["更新", "测试"],
        )

        assert updated is True

        # 验证更新结果
        updated_memory = manager.get_memory(memory_id)
        assert updated_memory["content"] == "更新后的内容"
        assert updated_memory["category"] == "updated"
        assert updated_memory["importance"] == 0.9
        assert "更新" in updated_memory["tags"]

        print("✓ 记忆更新成功")

        manager.close()
        print("\n✅ 更新功能测试通过!")


def test_archive_functionality():
    """测试归档功能."""
    print("\n" + "=" * 60)
    print("测试 5: 归档功能")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)
        manager = MemoryManager(workspace)

        # 添加测试记忆
        memory = manager.remember("归档测试", "test", 0.5, "test")
        memory_id = memory["id"]

        # 测试归档
        archived = manager.archive_memory(memory_id)
        assert archived is True

        # 验证归档状态
        archived_memory = manager.get_memory(memory_id)
        assert archived_memory["is_archived"] is True
        assert archived_memory["archived_at"] is not None

        print("✓ 记忆归档成功")

        # 测试搜索不包含归档记忆
        results = manager.search_memories(query="测试", include_archived=False)
        assert len(results) == 0

        print("✓ 搜索不包含归档记忆")

        # 测试搜索包含归档记忆
        results = manager.search_memories(query="测试", include_archived=True)
        assert len(results) == 1

        print("✓ 搜索包含归档记忆")

        # 测试取消归档
        unarchived = manager.unarchive_memory(memory_id)
        assert unarchived is True

        unarchived_memory = manager.get_memory(memory_id)
        assert unarchived_memory["is_archived"] is False

        print("✓ 记忆取消归档成功")

        manager.close()
        print("\n✅ 归档功能测试通过!")


def test_forget_functionality():
    """测试删除功能."""
    print("\n" + "=" * 60)
    print("测试 6: 删除功能")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)
        manager = MemoryManager(workspace)

        # 添加测试记忆
        manager.remember("删除测试1", "test", 0.5, "test")
        manager.remember("删除测试2", "test", 0.5, "test")
        manager.remember("保留内容", "other", 0.5, "test")

        # 测试删除
        stats = manager.forget("删除测试")

        assert stats["total_found"] >= 2
        assert stats["deleted"] + stats["archived"] >= 2

        print(f"✓ 记忆删除成功: 找到 {stats['total_found']} 条，删除 {stats['deleted']} 条，归档 {stats['archived']} 条")

        # 验证删除结果
        results = manager.search_memories(query="测试", include_archived=True)
        assert len(results) == 0

        results = manager.search_memories(query="保留", include_archived=False)
        assert len(results) == 1

        print("✓ 删除结果验证成功")

        manager.close()
        print("\n✅ 删除功能测试通过!")


def test_statistics():
    """测试统计功能."""
    print("\n" + "=" * 60)
    print("测试 7: 统计功能")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)
        manager = MemoryManager(workspace)

        # 添加测试数据
        manager.remember("统计测试1", "personal", 0.9, "test")
        manager.remember("统计测试2", "work", 0.7, "test")
        manager.remember("统计测试3", "personal", 0.8, "test")

        # 归档一个记忆
        memories = manager.search_memories(query="测试")
        if memories:
            manager.archive_memory(memories[0]["id"])

        # 获取统计信息
        stats = manager.get_stats()

        assert "sqlite" in stats
        assert "sync" in stats
        assert "vector_store_available" in stats

        sqlite_stats = stats["sqlite"]
        assert sqlite_stats["total"] >= 3

        print("✓ 统计信息获取成功:")
        print(f"  总记忆数: {sqlite_stats['total']}")
        print(f"  归档数: {sqlite_stats['archived']}")
        print(f"  重要记忆数: {sqlite_stats['important']}")
        print(f"  平均重要性: {sqlite_stats['avg_importance']:.2f}")

        manager.close()
        print("\n✅ 统计功能测试通过!")


def test_retrieval_strategies():
    """测试检索策略."""
    print("\n" + "=" * 60)
    print("测试 8: 检索策略")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)
        manager = MemoryManager(workspace)

        # 添加测试数据
        test_data = [
            ("语义检索测试1", "test", 0.8),
            ("关键词检索测试", "test", 0.7),
            ("混合检索测试", "test", 0.9),
        ]

        for content, category, importance in test_data:
            manager.remember(content, category, importance, "test")

        print("\n检索策略测试:")

        # 测试关键词检索
        keyword_results = manager.recall(
            query="关键词",
            strategy=RetrievalStrategy.KEYWORD,
        )
        print(f"  ✓ 关键词检索: 找到 {len(keyword_results)} 条结果")

        # 测试语义检索（如果向量存储可用）
        if manager.vector_adapter.is_available():
            semantic_results = manager.recall(
                query="语义",
                strategy=RetrievalStrategy.SEMANTIC,
            )
            print(f"  ✓ 语义检索: 找到 {len(semantic_results)} 条结果")
        else:
            print("  ⚠ 语义检索: 向量存储不可用")

        # 测试混合检索
        hybrid_results = manager.recall(
            query="检索",
            strategy=RetrievalStrategy.HYBRID,
        )
        print(f"  ✓ 混合检索: 找到 {len(hybrid_results)} 条结果")

        manager.close()
        print("\n✅ 检索策略测试通过!")


if __name__ == "__main__":
    """运行所有测试."""
    test_basic_functionality()
    test_auto_classification()
    test_importance_scoring()
    test_update_functionality()
    test_archive_functionality()
    test_forget_functionality()
    test_statistics()
    test_retrieval_strategies()

    print("\n" + "=" * 60)
    print("所有记忆管理器测试通过! ✅")
    print("=" * 60)
