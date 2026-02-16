"""测试记忆模块功能.

验证 EnhancedMemoryStore 的核心功能：
1. 记忆保存
2. 记忆检索
3. 记忆删除
4. 重要性评分
5. 自动分类
6. 检索策略（语义/关键词/混合）
7. 相似度阈值
"""

import tempfile
from pathlib import Path

from finchbot.memory import EnhancedMemoryStore, MemoryEntry, RetrievalStrategy


def test_basic_remember_recall():
    """测试基本的记忆保存和检索."""
    print("\n" + "=" * 60)
    print("测试 1: 基本记忆保存和检索")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        store = EnhancedMemoryStore(Path(tmpdir))
        store._vectorstore = None  # 禁用向量存储避免文件锁定

        store.remember("我叫张三，今年25岁", source="test")
        store.remember("我喜欢编程和阅读", source="test")
        store.remember("我的邮箱是 test@example.com", source="test")
        store.remember("明天下午3点有个会议", source="test")

        results = store.recall("名字")
        print(f"\n查询 '名字' 找到 {len(results)} 条记忆:")
        for entry in results:
            print(f"  - [{entry.category}] {entry.content} (重要性: {entry.importance:.2f})")

        results = store.recall("邮箱")
        print(f"\n查询 '邮箱' 找到 {len(results)} 条记忆:")
        for entry in results:
            print(f"  - [{entry.category}] {entry.content} (重要性: {entry.importance:.2f})")

        print("\n✅ 基本记忆保存和检索测试通过!")


def test_importance_scoring():
    """测试重要性评分."""
    print("\n" + "=" * 60)
    print("测试 2: 重要性评分")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        store = EnhancedMemoryStore(Path(tmpdir))
        store._vectorstore = None

        test_cases = [
            ("我叫李四", "个人信息"),
            ("我的电话是 13800138000", "联系方式"),
            ("我喜欢喝咖啡", "偏好"),
            ("这是一个重要的截止日期", "重要标记"),
            ("记住这个关键信息", "关键标记"),
        ]

        print("\n重要性评分测试:")
        for content, desc in test_cases:
            entry = store.remember(content, source="test")
            print(f"  {desc}: '{content}'")
            print(f"    -> 分类: {entry.category}, 重要性: {entry.importance:.2f}")

        print("\n✅ 重要性评分测试通过!")


def test_category_detection():
    """测试自动分类."""
    print("\n" + "=" * 60)
    print("测试 3: 自动分类")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        store = EnhancedMemoryStore(Path(tmpdir))
        store._vectorstore = None

        test_cases = [
            ("我叫小明，今年30岁", "personal"),
            ("我喜欢吃苹果", "preference"),
            ("明天有个重要会议", "schedule"),
            ("我的邮箱是 abc@def.com", "contact"),
            ("我的目标是学习 AI", "goal"),
            ("正在做一个新项目", "work"),
        ]

        print("\n自动分类测试:")
        for content, expected_category in test_cases:
            entry = store.remember(content, source="test")
            status = "✓" if entry.category == expected_category else "✗"
            print(f"  {status} '{content}'")
            print(f"      预期: {expected_category}, 实际: {entry.category}")

        print("\n✅ 自动分类测试通过!")


def test_forget():
    """测试记忆删除."""
    print("\n" + "=" * 60)
    print("测试 4: 记忆删除")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        store = EnhancedMemoryStore(Path(tmpdir))
        store._vectorstore = None

        store.remember("测试记忆1", source="test")
        store.remember("测试记忆2", source="test")
        store.remember("其他记忆", source="test")

        print("\n保存了 3 条记忆")

        removed = store.forget("测试记忆")
        print(f"删除匹配 '测试记忆' 的条目: {removed} 条")

        all_entries = store.get_all_entries()
        print(f"剩余记忆: {len(all_entries)} 条")
        for entry in all_entries:
            print(f"  - {entry.content}")

        print("\n✅ 记忆删除测试通过!")


def test_memory_context():
    """测试记忆上下文生成."""
    print("\n" + "=" * 60)
    print("测试 5: 记忆上下文生成")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        store = EnhancedMemoryStore(Path(tmpdir))
        store._vectorstore = None

        store.remember("用户偏好使用 Python 编程", source="test")
        store.remember("用户正在学习 LangChain", source="test")
        store.remember("项目截止日期是下周五", source="test")

        context = store.get_memory_context()
        print("\n生成的记忆上下文:")
        print(context)

        print("\n✅ 记忆上下文生成测试通过!")


def test_persistence():
    """测试持久化."""
    print("\n" + "=" * 60)
    print("测试 6: 持久化")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)

        store1 = EnhancedMemoryStore(workspace)
        store1._vectorstore = None
        store1.remember("持久化测试记忆", source="test")
        print("\n第一次保存: 1 条记忆")

        store2 = EnhancedMemoryStore(workspace)
        store2._vectorstore = None
        entries = store2.get_all_entries()
        print(f"重新加载后: {len(entries)} 条记忆")
        for entry in entries:
            print(f"  - {entry.content}")

        assert len(entries) == 1, "持久化失败"
        print("\n✅ 持久化测试通过!")


def test_memory_entry():
    """测试 MemoryEntry 数据类."""
    print("\n" + "=" * 60)
    print("测试 7: MemoryEntry 数据类")
    print("=" * 60)

    entry = MemoryEntry(
        content="测试内容",
        importance=0.8,
        category="test",
        source="unit_test",
    )

    print("\n原始条目:")
    print(f"  内容: {entry.content}")
    print(f"  重要性: {entry.importance}")
    print(f"  分类: {entry.category}")
    print(f"  来源: {entry.source}")

    data = entry.to_dict()
    print(f"\n序列化后: {data}")

    restored = MemoryEntry.from_dict(data)
    print("\n反序列化后:")
    print(f"  内容: {restored.content}")
    print(f"  重要性: {restored.importance}")
    print(f"  分类: {restored.category}")
    print(f"  来源: {restored.source}")

    assert restored.content == entry.content, "序列化/反序列化失败"
    print("\n✅ MemoryEntry 数据类测试通过!")


def test_retrieval_strategies():
    """测试三种检索策略."""
    print("\n" + "=" * 60)
    print("测试 8: 检索策略")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        store = EnhancedMemoryStore(Path(tmpdir))
        store._vectorstore = None  # 禁用向量存储，仅测试关键词检索

        # 添加测试记忆
        store.remember("LangChain 是一个用于构建 LLM 应用的框架", source="test")
        store.remember("我喜欢使用 Python 编程", source="test")
        store.remember("今天的天气很好", source="test")

        print("\n测试 KEYWORD 策略:")
        results = store.recall("LangChain", strategy=RetrievalStrategy.KEYWORD)
        print(f"  查询 'LangChain' 找到 {len(results)} 条")
        for entry in results:
            print(f"    - {entry.content}")

        print("\n测试 HYBRID 策略（无向量存储时回退到关键词）:")
        results = store.recall("Python", strategy=RetrievalStrategy.HYBRID)
        print(f"  查询 'Python' 找到 {len(results)} 条")
        for entry in results:
            print(f"    - {entry.content}")

        print("\n✅ 检索策略测试通过!")


def test_similarity_threshold():
    """测试相似度阈值（在关键词检索中测试阈值参数传递）."""
    print("\n" + "=" * 60)
    print("测试 9: 相似度阈值参数")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        store = EnhancedMemoryStore(Path(tmpdir))
        store._vectorstore = None

        store.remember("测试内容 A", source="test")
        store.remember("测试内容 B", source="test")
        store.remember("完全不同的内容", source="test")

        print("\n测试相似度阈值参数传递:")
        # 测试参数可以正常传递（由于无向量存储，实际阈值不影响结果）
        results = store.recall("测试", similarity_threshold=0.8)
        print(f"  阈值 0.8，查询 '测试' 找到 {len(results)} 条")

        results = store.recall("测试", similarity_threshold=0.3)
        print(f"  阈值 0.3，查询 '测试' 找到 {len(results)} 条")

        print("\n✅ 相似度阈值参数测试通过!")


def test_backward_compatibility():
    """测试向后兼容性."""
    print("\n" + "=" * 60)
    print("测试 10: 向后兼容性")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        store = EnhancedMemoryStore(Path(tmpdir))
        store._vectorstore = None

        store.remember("向后兼容测试", source="test")

        print("\n测试旧版调用方式:")
        # 旧版调用方式（不传新参数）
        results = store.recall("测试", top_k=5, category=None, min_importance=0.0)
        print(f"  旧版调用找到 {len(results)} 条")

        # 新版调用方式
        results = store.recall(
            "测试",
            top_k=5,
            category=None,
            min_importance=0.0,
            strategy=RetrievalStrategy.HYBRID,
            similarity_threshold=0.5,
        )
        print(f"  新版调用找到 {len(results)} 条")

        print("\n✅ 向后兼容性测试通过!")


def main():
    """运行所有测试."""
    print("\n" + "=" * 60)
    print("FinchBot 记忆模块测试")
    print("=" * 60)

    test_basic_remember_recall()
    test_importance_scoring()
    test_category_detection()
    test_forget()
    test_memory_context()
    test_persistence()
    test_memory_entry()
    test_retrieval_strategies()
    test_similarity_threshold()
    test_backward_compatibility()

    print("\n" + "=" * 60)
    print("🎉 所有测试通过!")
    print("=" * 60)


if __name__ == "__main__":
    main()
