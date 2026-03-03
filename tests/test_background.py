"""后台任务工具测试."""

from __future__ import annotations

import pytest

from finchbot.agent.tools.background import (
    cancel_task,
    check_task_status,
    get_job_manager,
    get_task_result,
    start_background_task,
)


class TestJobManager:
    """JobManager 测试."""

    def test_singleton(self) -> None:
        """测试单例模式."""
        manager1 = get_job_manager()
        manager2 = get_job_manager()
        assert manager1 is manager2

    def test_create_job(self) -> None:
        """测试创建任务."""
        manager = get_job_manager()
        manager._jobs.clear()

        job_id = manager.create_job()
        assert job_id is not None
        assert len(job_id) == 8

        status = manager.get_status(job_id)
        assert status is not None
        assert status.status == "pending"

    def test_create_job_with_label(self) -> None:
        """测试创建带标签的任务."""
        manager = get_job_manager()
        manager._jobs.clear()

        job_id = manager.create_job(label="Test Label")
        status = manager.get_status(job_id)
        assert status is not None
        assert status.label == "Test Label"

    def test_update_status(self) -> None:
        """测试更新状态."""
        manager = get_job_manager()
        manager._jobs.clear()

        job_id = manager.create_job()
        manager.update_status(job_id, "running")
        assert manager.get_status(job_id).status == "running"

        manager.update_status(job_id, "completed", result="Done")
        status = manager.get_status(job_id)
        assert status.status == "completed"
        assert status.result == "Done"

    def test_cancel_job(self) -> None:
        """测试取消任务."""
        manager = get_job_manager()
        manager._jobs.clear()

        job_id = manager.create_job()
        manager.update_status(job_id, "cancelled")
        assert manager.get_status(job_id).status == "cancelled"

    def test_list_jobs(self) -> None:
        """测试列出任务."""
        manager = get_job_manager()
        manager._jobs.clear()

        job_id1 = manager.create_job()
        job_id2 = manager.create_job()

        manager.update_status(job_id1, "completed", result="Done")

        jobs = manager.list_jobs(include_completed=True)
        assert len(jobs) == 2

        jobs = manager.list_jobs(include_completed=False)
        assert len(jobs) == 1
        assert jobs[0].job_id == job_id2

    def test_cleanup_old_jobs(self) -> None:
        """测试清理旧任务."""
        manager = get_job_manager()
        manager._jobs.clear()

        job_id = manager.create_job()
        manager.update_status(job_id, "completed", result="Done")

        assert len(manager.list_jobs()) == 1

        cleaned = manager.cleanup_old_jobs(max_age_hours=0)
        assert cleaned == 1
        assert len(manager.list_jobs()) == 0


class TestBackgroundTools:
    """后台任务工具测试."""

    @pytest.mark.asyncio
    async def test_start_background_task(self) -> None:
        """测试启动后台任务."""
        manager = get_job_manager()
        manager._jobs.clear()

        result = await start_background_task.ainvoke({"task_description": "Test task"})

        assert "已启动" in result or "started" in result.lower() or "ID" in result

    def test_check_task_status(self) -> None:
        """测试检查任务状态."""
        manager = get_job_manager()
        manager._jobs.clear()

        job_id = manager.create_job()
        result = check_task_status.invoke({"job_id": job_id})
        assert job_id in result
        assert "pending" in result

        result = check_task_status.invoke({"job_id": "nonexistent"})
        assert "not found" in result.lower() or "不存在" in result

    def test_get_task_result(self) -> None:
        """测试获取任务结果."""
        manager = get_job_manager()
        manager._jobs.clear()

        job_id = manager.create_job()

        result = get_task_result.invoke({"job_id": job_id})
        assert "not completed" in result.lower() or "尚未完成" in result

        manager.update_status(job_id, "completed", result="Success!")
        result = get_task_result.invoke({"job_id": job_id})
        assert "Success" in result

    def test_cancel_task_tool(self) -> None:
        """测试取消任务工具."""
        manager = get_job_manager()
        manager._jobs.clear()

        job_id = manager.create_job()
        manager.update_status(job_id, "cancelled")
        result = cancel_task.invoke({"job_id": job_id})
        assert "cancelled" in result.lower() or "已取消" in result or "尚未完成" in result

    def test_list_background_tasks(self) -> None:
        """测试列出后台任务工具."""
        from finchbot.agent.tools.background import list_background_tasks

        manager = get_job_manager()
        manager._jobs.clear()

        result = list_background_tasks.invoke({"include_completed": False})
        assert "No background tasks" in result

        manager.create_job(label="Test Job")
        result = list_background_tasks.invoke({"include_completed": False})
        assert "Test Job" in result or "pending" in result
