"""测试记忆模块功能."""

import tempfile
from pathlib import Path

from finchbot.memory.enhanced import EnhancedMemoryStore


def main():
    """运行记忆模块测试."""
    print("=" * 60)
    print("FinchBot 记忆模块测试")
    print("=" * 60)

    print("\n创建临时目录...")
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"临时目录: {tmpdir}")
        store = EnhancedMemoryStore(Path(tmpdir))
        store._vectorstore = None  # 禁用向量存储加速测试

        print("\n1. 测试记忆保存...")
        entry = store.remember("我叫张三，今年25岁", source="test")
        print(f"   保存成功: {entry.content}")
        print(f"   分类: {entry.category}, 重要性: {entry.importance}")

        print("\n2. 测试记忆检索...")
        results = store.recall("张三")
        print(f"   找到 {len(results)} 条记忆")
        for e in results:
            print(f"   - {e.content}")

        print("\n3. 测试持久化...")
        store2 = EnhancedMemoryStore(Path(tmpdir))
        store2._vectorstore = None
        entries = store2.get_all_entries()
        print(f"   重新加载后有 {len(entries)} 条记忆")

        print("\n4. 测试自动分类...")
        test_cases = [
            "我叫小明",
            "我喜欢编程",
            "明天有会议",
            "我的邮箱是 test@example.com",
            "这是一个重要的项目",
            "记住这个关键信息",
        ]
        for content in test_cases:
            e = store.remember(content, source="test")
            print(f'   "{content}" -> 分类: {e.category}, 重要性: {e.importance:.2f}')

        print("\n5. 测试记忆删除...")
        store.remember("临时记忆1", source="test")
        store.remember("临时记忆2", source="test")
        print(f"   删除前: {len(store.get_all_entries())} 条记忆")
        removed = store.forget("临时记忆")
        print(f"   删除了 {removed} 条")
        print(f"   删除后: {len(store.get_all_entries())} 条记忆")

        print("\n6. 测试记忆上下文生成...")
        context = store.get_memory_context(max_entries=5)
        print("   生成的记忆上下文:")
        for line in context.split("\n"):
            print(f"   {line}")

        print("\n" + "=" * 60)
        print("✅ 所有测试通过!")
        print("=" * 60)


if __name__ == "__main__":
    main()
