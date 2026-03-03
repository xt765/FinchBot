"""定时任务服务测试.

测试新的 CronService API，支持三种调度模式。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from finchbot.cron import CronJob, CronSchedule, CronService


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
    async def test_create_cron_job(self, cron_service: CronService) -> None:
        """测试创建 cron 表达式任务."""
        schedule = CronSchedule(kind="cron", expr="0 9 * * *")
        job = cron_service.add_job(
            name="Test Job",
            schedule=schedule,
            message="Test message",
        )

        assert job.id is not None
        assert job.name == "Test Job"
        assert job.schedule.kind == "cron"
        assert job.schedule.expr == "0 9 * * *"
        assert job.enabled is True
        assert job.state.next_run_at_ms is not None

    @pytest.mark.asyncio
    async def test_create_every_job(self, cron_service: CronService) -> None:
        """测试创建间隔任务."""
        schedule = CronSchedule(kind="every", every_ms=60000)
        job = cron_service.add_job(
            name="Every Minute Job",
            schedule=schedule,
            message="Run every minute",
        )

        assert job.id is not None
        assert job.schedule.kind == "every"
        assert job.schedule.every_ms == 60000

    @pytest.mark.asyncio
    async def test_create_at_job(self, cron_service: CronService) -> None:
        """测试创建一次性任务."""
        import time

        at_ms = int(time.time() * 1000) + 3600000
        schedule = CronSchedule(kind="at", at_ms=at_ms)
        job = cron_service.add_job(
            name="One-time Job",
            schedule=schedule,
            message="Run once",
            delete_after_run=True,
        )

        assert job.id is not None
        assert job.schedule.kind == "at"
        assert job.schedule.at_ms == at_ms
        assert job.delete_after_run is True

    @pytest.mark.asyncio
    async def test_create_invalid_cron(self, cron_service: CronService) -> None:
        """测试创建无效 cron 表达式的任务.

        validate() 只检查 expr 是否存在，不检查表达式有效性。
        无效表达式的任务会被创建，但 next_run_at_ms 为 None。
        """
        schedule = CronSchedule(kind="cron", expr="invalid cron")
        schedule.validate()

        job = cron_service.add_job(
            name="Invalid Job",
            schedule=schedule,
            message="Test",
        )
        assert job.state.next_run_at_ms is None

    @pytest.mark.asyncio
    async def test_invalid_timezone(self, cron_service: CronService) -> None:
        """测试无效时区."""
        schedule = CronSchedule(kind="cron", expr="0 9 * * *", tz="Invalid/Timezone")

        with pytest.raises(ValueError, match="Invalid timezone"):
            schedule.validate()

    @pytest.mark.asyncio
    async def test_timezone_with_wrong_kind(self, cron_service: CronService) -> None:
        """测试时区只能用于 cron 类型."""
        schedule = CronSchedule(kind="every", every_ms=60000, tz="Asia/Shanghai")

        with pytest.raises(ValueError, match="tz can only be used with 'cron' schedule"):
            schedule.validate()

    @pytest.mark.asyncio
    async def test_delete_job(self, cron_service: CronService) -> None:
        """测试删除任务."""
        schedule = CronSchedule(kind="cron", expr="0 9 * * *")
        job = cron_service.add_job(
            name="To Delete",
            schedule=schedule,
            message="Delete me",
        )

        result = cron_service.remove_job(job.id)
        assert result is True

        result = cron_service.remove_job(job.id)
        assert result is False

    @pytest.mark.asyncio
    async def test_list_jobs(self, cron_service: CronService) -> None:
        """测试列出任务."""
        schedule1 = CronSchedule(kind="cron", expr="0 9 * * *")
        schedule2 = CronSchedule(kind="cron", expr="0 18 * * *")

        cron_service.add_job(name="Job 1", schedule=schedule1, message="Message 1")
        cron_service.add_job(name="Job 2", schedule=schedule2, message="Message 2")

        jobs = cron_service.list_jobs()
        assert len(jobs) == 2

    @pytest.mark.asyncio
    async def test_toggle_job(self, cron_service: CronService) -> None:
        """测试启用/禁用任务."""
        schedule = CronSchedule(kind="cron", expr="0 9 * * *")
        job = cron_service.add_job(
            name="Toggle Test",
            schedule=schedule,
            message="Toggle me",
        )

        updated = cron_service.enable_job(job.id, enabled=False)
        assert updated is not None
        assert updated.enabled is False

        updated = cron_service.enable_job(job.id, enabled=True)
        assert updated is not None
        assert updated.enabled is True

    @pytest.mark.asyncio
    async def test_run_job(self, cron_service: CronService) -> None:
        """测试手动执行任务."""
        executed = []

        async def on_job(job: CronJob) -> str:
            executed.append(job.name)
            return f"Executed: {job.name}"

        cron_service.on_job = on_job

        schedule = CronSchedule(kind="cron", expr="0 9 * * *")
        job = cron_service.add_job(
            name="Run Now Test",
            schedule=schedule,
            message="Run me now",
        )

        result = await cron_service.run_job(job.id, force=True)
        assert result is True
        assert "Run Now Test" in executed
        assert job.state.last_status == "ok"

    @pytest.mark.asyncio
    async def test_persistence(self, temp_workspace: Path) -> None:
        """测试持久化."""
        schedule = CronSchedule(kind="cron", expr="0 9 * * *")

        service1 = CronService(temp_workspace / "data")
        await service1.start()

        job = service1.add_job(
            name="Persistent Job",
            schedule=schedule,
            message="Should persist",
        )
        job_id = job.id
        await service1.stop()

        service2 = CronService(temp_workspace / "data")
        await service2.start()

        loaded_job = service2.get_job(job_id)
        assert loaded_job is not None
        assert loaded_job.name == "Persistent Job"

        await service2.stop()

    @pytest.mark.asyncio
    async def test_job_status_tracking(self, cron_service: CronService) -> None:
        """测试任务状态跟踪."""
        schedule = CronSchedule(kind="cron", expr="0 9 * * *")
        job = cron_service.add_job(
            name="Status Test",
            schedule=schedule,
            message="Track status",
        )

        assert job.state.last_status is None
        assert job.state.last_error is None

        async def on_job(j: CronJob) -> str:
            return "Done"

        cron_service.on_job = on_job
        await cron_service.run_job(job.id, force=True)

        assert job.state.last_status == "ok"
        assert job.state.last_run_at_ms is not None

    @pytest.mark.asyncio
    async def test_job_error_tracking(self, cron_service: CronService) -> None:
        """测试任务错误跟踪."""
        schedule = CronSchedule(kind="cron", expr="0 9 * * *")
        job = cron_service.add_job(
            name="Error Test",
            schedule=schedule,
            message="Will fail",
        )

        async def on_job(j: CronJob) -> str:
            raise RuntimeError("Test error")

        cron_service.on_job = on_job
        await cron_service.run_job(job.id, force=True)

        assert job.state.last_status == "error"
        assert "Test error" in job.state.last_error


class TestCronSchedule:
    """CronSchedule 测试."""

    def test_cron_schedule(self) -> None:
        """测试 cron 调度."""
        schedule = CronSchedule(kind="cron", expr="0 9 * * *")
        schedule.validate()

        assert schedule.kind == "cron"
        assert schedule.expr == "0 9 * * *"

    def test_every_schedule(self) -> None:
        """测试间隔调度."""
        schedule = CronSchedule(kind="every", every_ms=60000)
        schedule.validate()

        assert schedule.kind == "every"
        assert schedule.every_ms == 60000

    def test_at_schedule(self) -> None:
        """测试一次性调度."""
        schedule = CronSchedule(kind="at", at_ms=1700000000000)
        schedule.validate()

        assert schedule.kind == "at"
        assert schedule.at_ms == 1700000000000


class TestCronJob:
    """CronJob 模型测试."""

    def test_create_cron_job(self) -> None:
        """测试创建 CronJob."""
        schedule = CronSchedule(kind="cron", expr="0 9 * * *")
        job = CronJob(
            id="test123",
            name="Test Job",
            schedule=schedule,
        )

        assert job.id == "test123"
        assert job.name == "Test Job"
        assert job.enabled is True

    def test_cron_job_with_payload(self) -> None:
        """测试带载荷的 CronJob."""
        from finchbot.cron import CronPayload

        schedule = CronSchedule(kind="cron", expr="0 */2 * * *")
        payload = CronPayload(
            message="Process data",
            deliver=True,
            channel="telegram",
            to="user123",
        )
        job = CronJob(
            id="test456",
            name="Job with Payload",
            schedule=schedule,
            payload=payload,
        )

        assert job.payload.message == "Process data"
        assert job.payload.deliver is True
        assert job.payload.channel == "telegram"
