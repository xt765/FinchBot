"""测试SQLite存储层功能.

验证SQLiteStore的核心功能：
1. 记忆添加和获取
2. 记忆更新和删除
3. 搜索功能
4. 分类管理
5. 访问日志记录
"""

import tempfile
from pathlib import Path

from finchbot.memory.sqlite_store import SQLiteStore


def test_basic_crud():
    """测试基本的CRUD操作."""
    print("\n" + "=" * 60)
    print("测试 1: 基本CRUD操作")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "memory.db"
        store = SQLiteStore(db_path)

        # 测试添加记忆
        memory_id = store.remember(
            content="我叫张三，今年25岁",
            category="personal",
            importance=0.8,
            source="test",
            tags=["个人信息", "年龄"],
            metadata={"age": 25, "gender": "male"},
        )
        print(f"✓ 记忆添加成功: {memory_id[:8]}...")

        # 测试获取记忆
        memory = store.get_memory(memory_id)
        assert memory is not None
        assert memory["content"] == "我叫张三，今年25岁"
        assert memory["category"] == "personal"
        assert memory["importance"] == 0.8
        print(f"✓ 记忆获取成功: {memory['content'][:20]}...")

        # 测试更新记忆
        updated = store.update_memory(
            memory_id=memory_id,
            content="我叫张三，今年26岁",
            importance=0.9,
            tags=["个人信息", "年龄", "更新"],
        )
        assert updated is True

        memory = store.get_memory(memory_id)
        assert memory["content"] == "我叫张三，今年26岁"
        assert memory["importance"] == 0.9
        assert "更新" in memory["tags"]
        print("✓ 记忆更新成功")

        # 测试删除记忆
        deleted = store.delete_memory(memory_id)
        assert deleted is True

        memory = store.get_memory(memory_id)
        assert memory is None
        print("✓ 记忆删除成功")

        store.close()
        print("\n✅ 基本CRUD操作测试通过!")


def test_search_functionality():
    """测试搜索功能."""
    print("\n" + "=" * 60)
    print("测试 2: 搜索功能")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "memory.db"
        store = SQLiteStore(db_path)

        # 添加测试数据
        test_data = [
            ("我叫李四，喜欢编程", "personal", 0.7),
            ("我的邮箱是 test@example.com", "contact", 0.9),
            ("明天下午3点有个会议", "work", 0.6),
            ("我喜欢吃苹果", "preference", 0.5),
            ("我的目标是学习AI", "goal", 0.8),
        ]

        for content, category, importance in test_data:
            store.remember(content, category, importance, "test")

        # 测试关键词搜索
        results = store.search_memories(query="邮箱")
        assert len(results) == 1
        assert "test@example.com" in results[0]["content"]
        print(f"✓ 关键词搜索成功: 找到 {len(results)} 条结果")

        # 测试分类过滤
        results = store.search_memories(category="personal")
        assert len(results) == 1
        assert "李四" in results[0]["content"]
        print(f"✓ 分类过滤成功: 找到 {len(results)} 条结果")

        # 测试重要性过滤
        results = store.search_memories(min_importance=0.8)
        assert len(results) >= 2  # 邮箱(0.9) + 目标(0.8)
        print(f"✓ 重要性过滤成功: 找到 {len(results)} 条重要记忆")

        store.close()
        print("\n✅ 搜索功能测试通过!")


def test_archive_functionality():
    """测试归档功能."""
    print("\n" + "=" * 60)
    print("测试 3: 归档功能")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "memory.db"
        store = SQLiteStore(db_path)

        # 添加测试记忆
        memory_id = store.remember("这是一个测试记忆", "test", 0.5, "test")

        # 测试归档
        archived = store.archive_memory(memory_id)
        assert archived is True

        memory = store.get_memory(memory_id)
        assert memory["is_archived"] is True
        assert memory["archived_at"] is not None
        print("✓ 记忆归档成功")

        # 测试搜索不包含归档记忆
        results = store.search_memories(query="测试", include_archived=False)
        assert len(results) == 0
        print("✓ 搜索不包含归档记忆")

        # 测试搜索包含归档记忆
        results = store.search_memories(query="测试", include_archived=True)
        assert len(results) == 1
        print("✓ 搜索包含归档记忆")

        # 测试取消归档
        unarchived = store.unarchive_memory(memory_id)
        assert unarchived is True

        memory = store.get_memory(memory_id)
        assert memory["is_archived"] is False
        assert memory["archived_at"] is None
        print("✓ 记忆取消归档成功")

        store.close()
        print("\n✅ 归档功能测试通过!")


def test_access_logging():
    """测试访问日志记录."""
    print("\n" + "=" * 60)
    print("测试 4: 访问日志记录")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "memory.db"
        store = SQLiteStore(db_path)

        # 添加测试记忆
        memory_id = store.remember("访问日志测试", "test", 0.5, "test")

        # 记录访问
        store.record_access(memory_id, "read", "test_context")

        # 获取记忆并检查访问统计
        memory = store.get_memory(memory_id)
        assert memory["access_count"] == 1
        assert memory["last_accessed"] is not None
        print(f"✓ 访问日志记录成功: 访问次数 {memory['access_count']}")

        # 再次记录访问
        store.record_access(memory_id, "write", "update_context")

        memory = store.get_memory(memory_id)
        assert memory["access_count"] == 2
        print("✓ 多次访问记录成功")

        store.close()
        print("\n✅ 访问日志记录测试通过!")


def test_category_management():
    """测试分类管理."""
    print("\n" + "=" * 60)
    print("测试 5: 分类管理")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "memory.db"
        store = SQLiteStore(db_path)

        # 添加分类
        category_id = store.add_category(
            name="工作",
            description="工作相关记忆",
            keywords=["会议", "项目", "截止日期", "任务"],
        )
        print(f"✓ 分类添加成功: {category_id[:8]}...")

        # 获取所有分类
        categories = store.get_categories()
        assert len(categories) == 1
        assert categories[0]["name"] == "工作"
        assert "会议" in categories[0]["keywords"]
        print(f"✓ 分类获取成功: {categories[0]['name']}")

        # 添加子分类
        store.add_category(
            name="会议记录",
            description="会议相关记录",
            keywords=["会议纪要", "参会人员", "决议"],
            parent_id=category_id,
        )
        print("✓ 子分类添加成功")

        categories = store.get_categories()
        assert len(categories) == 2
        print(f"✓ 分类总数正确: {len(categories)}")

        store.close()
        print("\n✅ 分类管理测试通过!")


def test_statistics():
    """测试统计功能."""
    print("\n" + "=" * 60)
    print("测试 6: 统计功能")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "memory.db"
        store = SQLiteStore(db_path)

        # 添加测试数据
        store.remember("记忆1", "personal", 0.9, "test")
        store.remember("记忆2", "work", 0.7, "test")
        store.remember("记忆3", "personal", 0.8, "test")

        # 归档一个记忆
        memories = store.search_memories(query="记忆")
        if memories:
            store.archive_memory(memories[0]["id"])

        # 获取统计信息
        stats = store.get_memory_stats()
        assert stats["total"] == 3
        assert stats["archived"] == 1
        assert stats["important"] >= 2  # 重要性 >= 0.8
        assert stats["avg_importance"] > 0.7

        print("✓ 统计信息获取成功:")
        print(f"  总记忆数: {stats['total']}")
        print(f"  归档数: {stats['archived']}")
        print(f"  重要记忆数: {stats['important']}")
        print(f"  平均重要性: {stats['avg_importance']:.2f}")
        print(f"  总访问次数: {stats['total_accesses']}")

        store.close()
        print("\n✅ 统计功能测试通过!")


def test_recent_and_important_memories():
    """测试最近和重要记忆获取."""
    print("\n" + "=" * 60)
    print("测试 7: 最近和重要记忆")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "memory.db"
        store = SQLiteStore(db_path)

        # 添加测试数据
        store.remember("重要记忆1", "personal", 0.95, "test")
        store.remember("普通记忆1", "work", 0.6, "test")
        store.remember("重要记忆2", "personal", 0.85, "test")
        store.remember("普通记忆2", "preference", 0.5, "test")

        # 测试重要记忆
        important = store.get_important_memories(min_importance=0.8)
        assert len(important) == 2
        for mem in important:
            assert mem["importance"] >= 0.8
        print(f"✓ 重要记忆获取成功: {len(important)} 条")

        # 测试最近记忆
        recent = store.get_recent_memories(days=7)
        assert len(recent) == 4
        print(f"✓ 最近记忆获取成功: {len(recent)} 条")

        store.close()
        print("\n✅ 最近和重要记忆测试通过!")


if __name__ == "__main__":
    """运行所有测试."""
    test_basic_crud()
    test_search_functionality()
    test_archive_functionality()
    test_access_logging()
    test_category_management()
    test_statistics()
    test_recent_and_important_memories()

    print("\n" + "=" * 60)
    print("所有SQLite存储层测试通过! ✅")
    print("=" * 60)
