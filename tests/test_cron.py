"""定时任务服务测试."""

from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from finchbot.cron.service import CronJob, CronService


class TestCronService:
    """CronService 测试."""

    @pytest.fixture
    def temp_workspace(self) -> Path:
        """创建临时工作目录."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    async def cron_service(self, temp_workspace: Path) -> CronService:
        """创建 CronService 实例."""
        service = CronService(temp_workspace / "data")
        await service.start()
        yield service
        await service.stop()

    @pytest.mark.asyncio
    async def test_create_job(self, cron_service: CronService) -> None:
        """测试创建任务."""
        job = await cron_service.create(
            name="Test Job",
            schedule="0 9 * * *",
            message="Test message",
        )

        assert job.cron_id is not None
        assert job.name == "Test Job"
        assert job.schedule == "0 9 * * *"
        assert job.enabled is True
        assert job.next_run_date is not None

    @pytest.mark.asyncio
    async def test_create_invalid_cron(self, cron_service: CronService) -> None:
        """测试创建无效 cron 表达式的任务."""
        with pytest.raises(ValueError, match="Invalid cron expression"):
            await cron_service.create(
                name="Invalid Job",
                schedule="invalid cron",
                message="Test",
            )

    @pytest.mark.asyncio
    async def test_delete_job(self, cron_service: CronService) -> None:
        """测试删除任务."""
        job = await cron_service.create(
            name="To Delete",
            schedule="0 9 * * *",
            message="Delete me",
        )

        result = await cron_service.delete(job.cron_id)
        assert result is True

        # 再次删除应该返回 False
        result = await cron_service.delete(job.cron_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_list_jobs(self, cron_service: CronService) -> None:
        """测试列出任务."""
        await cron_service.create(
            name="Job 1",
            schedule="0 9 * * *",
            message="Message 1",
        )
        await cron_service.create(
            name="Job 2",
            schedule="0 18 * * *",
            message="Message 2",
        )

        jobs = await cron_service.list()
        assert len(jobs) == 2

    @pytest.mark.asyncio
    async def test_toggle_job(self, cron_service: CronService) -> None:
        """测试启用/禁用任务."""
        job = await cron_service.create(
            name="Toggle Test",
            schedule="0 9 * * *",
            message="Toggle me",
        )

        # 禁用
        updated = await cron_service.toggle(job.cron_id, enabled=False)
        assert updated.enabled is False

        # 启用
        updated = await cron_service.toggle(job.cron_id, enabled=True)
        assert updated.enabled is True

    @pytest.mark.asyncio
    async def test_run_now(self, cron_service: CronService) -> None:
        """测试立即执行任务."""
        executed = []

        async def on_job(job: CronJob) -> str:
            executed.append(job.name)
            return f"Executed: {job.name}"

        cron_service.on_job(on_job)

        job = await cron_service.create(
            name="Run Now Test",
            schedule="0 9 * * *",
            message="Run me now",
        )

        result = await cron_service.run_now(job.cron_id)
        assert "Executed" in result
        assert "Run Now Test" in executed
        assert job.run_count == 1

    @pytest.mark.asyncio
    async def test_persistence(self, temp_workspace: Path) -> None:
        """测试持久化."""
        # 创建服务并添加任务
        service1 = CronService(temp_workspace / "data")
        await service1.start()

        job = await service1.create(
            name="Persistent Job",
            schedule="0 9 * * *",
            message="Should persist",
        )
        job_id = job.cron_id
        await service1.stop()

        # 创建新服务实例，应该能加载之前的任务
        service2 = CronService(temp_workspace / "data")
        await service2.start()

        loaded_job = await service2.get(job_id)
        assert loaded_job is not None
        assert loaded_job.name == "Persistent Job"

        await service2.stop()

    def test_compute_next_run(self, temp_workspace: Path) -> None:
        """测试计算下次执行时间."""
        service = CronService(temp_workspace / "data")

        # 每分钟执行
        next_run = service._compute_next_run("* * * * *")
        assert next_run is not None

        # 每天早上 9 点（本地时间）
        next_run = service._compute_next_run("0 9 * * *")
        assert next_run is not None

        # 解析时间（存储为 UTC，需转换为本地时间验证）
        dt = datetime.fromisoformat(next_run.replace("Z", "+00:00"))
        local_dt = dt.astimezone()
        assert local_dt.minute == 0
        assert local_dt.hour == 9


class TestCronJob:
    """CronJob 模型测试."""

    def test_create_cron_job(self) -> None:
        """测试创建 CronJob."""
        job = CronJob(
            cron_id="test123",
            name="Test Job",
            schedule="0 9 * * *",
            message="Test message",
        )

        assert job.cron_id == "test123"
        assert job.name == "Test Job"
        assert job.enabled is True
        assert job.run_count == 0

    def test_cron_job_with_input(self) -> None:
        """测试带输入数据的 CronJob."""
        job = CronJob(
            cron_id="test456",
            name="Job with Input",
            schedule="0 */2 * * *",
            message="Process data",
            input={"key": "value"},
        )

        assert job.input == {"key": "value"}
