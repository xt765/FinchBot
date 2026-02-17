"""测试向量存储同步功能.

验证DataSyncManager和VectorStoreAdapter的核心功能：
1. 数据同步调度
2. 向量存储操作
3. 数据一致性检查
"""

import tempfile
import time
from pathlib import Path

from finchbot.memory.sqlite_store import SQLiteStore
from finchbot.memory.vector_sync import DataSyncManager, VectorStoreAdapter


class MockVectorStore:
    """模拟向量存储用于测试."""

    def __init__(self):
        self.store = {}
        self.operations = []

    def add(self, id: str, content: str, metadata: dict) -> bool:
        self.store[id] = {"content": content, "metadata": metadata}
        self.operations.append(("add", id))
        return True

    def update(self, id: str, content: str, metadata: dict) -> bool:
        if id in self.store:
            self.store[id] = {"content": content, "metadata": metadata}
            self.operations.append(("update", id))
            return True
        return False

    def delete(self, id: str) -> bool:
        if id in self.store:
            del self.store[id]
            self.operations.append(("delete", id))
            return True
        return False

    def get(self, id: str) -> dict:
        return self.store.get(id)

    def get_all_ids(self) -> list:
        return list(self.store.keys())


def test_vector_store_adapter():
    """测试向量存储适配器."""
    print("\n" + "=" * 60)
    print("测试 1: 向量存储适配器")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        workspace = Path(tmpdir)

        # 创建模拟向量存储
        mock_store = MockVectorStore()

        # 创建适配器
        adapter = VectorStoreAdapter(workspace)
        adapter.vectorstore = mock_store  # 替换为模拟存储

        # 测试添加
        success = adapter.add(
            id="test_id_1",
            content="测试内容1",
            metadata={"category": "test", "importance": 0.8},
        )
        assert success is True
        assert mock_store.get("test_id_1") is not None
        print("✓ 向量存储添加成功")

        # 测试更新
        success = adapter.update(
            id="test_id_1",
            content="更新后的内容",
            metadata={"category": "test", "importance": 0.9},
        )
        assert success is True
        assert mock_store.get("test_id_1")["content"] == "更新后的内容"
        print("✓ 向量存储更新成功")

        # 测试删除
        success = adapter.delete("test_id_1")
        assert success is True
        assert mock_store.get("test_id_1") is None
        print("✓ 向量存储删除成功")

        # 测试获取所有ID
        adapter.add("test_id_2", "内容2", {"category": "test"})
        adapter.add("test_id_3", "内容3", {"category": "test"})

        ids = adapter.get_all_ids()
        assert len(ids) == 2
        assert "test_id_2" in ids
        assert "test_id_3" in ids
        print(f"✓ 获取所有ID成功: {len(ids)} 个")

        print("\n✅ 向量存储适配器测试通过!")


def test_data_sync_manager():
    """测试数据同步管理器."""
    print("\n" + "=" * 60)
    print("测试 2: 数据同步管理器")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        # 创建SQLite存储
        db_path = Path(tmpdir) / "memory.db"
        sqlite_store = SQLiteStore(db_path)

        # 创建模拟向量存储
        mock_store = MockVectorStore()

        # 创建数据同步管理器（缩短同步间隔以便测试）
        sync_manager = DataSyncManager(
            sqlite_store=sqlite_store,
            vector_store=mock_store,
            sync_interval=1,  # 1秒同步间隔
            max_retries=2,
        )

        # 添加测试记忆
        memory_id = sqlite_store.remember(
            content="同步测试记忆",
            category="test",
            importance=0.7,
            source="test",
        )
        print(f"✓ 记忆添加成功: {memory_id[:8]}...")

        # 调度同步
        sync_manager.schedule_sync(memory_id, "add")
        print("✓ 同步任务调度成功")

        # 等待同步完成
        time.sleep(2)

        # 检查同步状态
        status = sync_manager.get_sync_status()
        assert status["queue_size"] == 0
        assert status["successful_syncs"] >= 1
        print(f"✓ 同步完成状态: 队列大小 {status['queue_size']}, 成功同步 {status['successful_syncs']}")

        # 检查向量存储中是否有数据
        vector_item = mock_store.get(memory_id)
        assert vector_item is not None
        assert vector_item["content"] == "同步测试记忆"
        print("✓ 向量存储同步验证成功")

        # 测试更新同步
        sqlite_store.update_memory(memory_id, content="更新后的同步测试记忆")
        sync_manager.schedule_sync(memory_id, "update")

        time.sleep(2)

        vector_item = mock_store.get(memory_id)
        assert vector_item["content"] == "更新后的同步测试记忆"
        print("✓ 更新同步验证成功")

        # 测试删除同步
        sqlite_store.delete_memory(memory_id)
        sync_manager.schedule_sync(memory_id, "delete")

        time.sleep(2)

        vector_item = mock_store.get(memory_id)
        assert vector_item is None
        print("✓ 删除同步验证成功")

        # 停止同步管理器
        sync_manager.stop()

        sqlite_store.close()
        print("\n✅ 数据同步管理器测试通过!")


def test_sync_retry_logic():
    """测试同步重试逻辑."""
    print("\n" + "=" * 60)
    print("测试 3: 同步重试逻辑")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        # 创建SQLite存储
        db_path = Path(tmpdir) / "memory.db"
        sqlite_store = SQLiteStore(db_path)

        # 创建总是失败的模拟向量存储
        class FailingVectorStore:
            def add(self, id, content, metadata):
                raise Exception("模拟添加失败")

            def update(self, id, content, metadata):
                raise Exception("模拟更新失败")

            def delete(self, id):
                raise Exception("模拟删除失败")

        failing_store = FailingVectorStore()

        # 创建数据同步管理器
        sync_manager = DataSyncManager(
            sqlite_store=sqlite_store,
            vector_store=failing_store,
            sync_interval=1,
            max_retries=2,  # 最多重试2次
        )

        # 添加测试记忆并调度同步
        memory_id = sqlite_store.remember("重试测试", "test", 0.5, "test")
        sync_manager.schedule_sync(memory_id, "add")

        # 等待重试完成
        time.sleep(5)  # 给足够时间进行重试

        # 检查同步状态
        status = sync_manager.get_sync_status()
        assert status["failed_syncs"] >= 1  # 应该至少有一次失败
        print(f"✓ 重试逻辑验证: 失败同步 {status['failed_syncs']} 次")

        # 停止同步管理器
        sync_manager.stop()

        sqlite_store.close()
        print("\n✅ 同步重试逻辑测试通过!")


def test_full_sync_check():
    """测试全量同步检查."""
    print("\n" + "=" * 60)
    print("测试 4: 全量同步检查")
    print("=" * 60)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        # 创建SQLite存储
        db_path = Path(tmpdir) / "memory.db"
        sqlite_store = SQLiteStore(db_path)

        # 创建模拟向量存储
        mock_store = MockVectorStore()

        # 创建数据同步管理器
        sync_manager = DataSyncManager(
            sqlite_store=sqlite_store,
            vector_store=mock_store,
            sync_interval=1,
        )

        # 在SQLite中添加一些记忆
        memory_ids = []
        for i in range(3):
            memory_id = sqlite_store.remember(f"全量同步测试{i}", "test", 0.5, "test")
            memory_ids.append(memory_id)

        print(f"✓ 添加了 {len(memory_ids)} 个测试记忆")

        # 手动在向量存储中添加一个额外的记忆（模拟不一致）
        mock_store.add("extra_memory", "额外记忆", {"category": "extra"})

        # 等待全量同步检查
        time.sleep(3)

        # 检查向量存储中的记忆
        vector_ids = mock_store.get_all_ids()

        # 应该包含所有SQLite记忆
        for memory_id in memory_ids:
            assert memory_id in vector_ids

        # 额外的记忆应该被删除
        assert "extra_memory" not in vector_ids

        print(f"✓ 全量同步检查完成: 向量存储中有 {len(vector_ids)} 个记忆")

        # 停止同步管理器
        sync_manager.stop()

        sqlite_store.close()
        print("\n✅ 全量同步检查测试通过!")


if __name__ == "__main__":
    """运行所有测试."""
    test_vector_store_adapter()
    test_data_sync_manager()
    test_sync_retry_logic()
    test_full_sync_check()

    print("\n" + "=" * 60)
    print("所有向量存储同步测试通过! ✅")
    print("=" * 60)
