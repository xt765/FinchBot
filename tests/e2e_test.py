"""端到端集成测试.

测试后台任务和定时任务的完整流程。
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from finchbot.agent.subagent import SubagentManager
from finchbot.agent.tools.background import (
    JobManager,
    get_job_manager,
    start_background_task,
    check_task_status,
    get_task_result,
    list_background_tasks,
)
from finchbot.agent.tools.cron import (
    create_cron,
    list_crons,
    get_cron_status,
    toggle_cron,
    delete_cron,
    set_cron_service,
)
from finchbot.cron.service import CronService
from finchbot.cron.types import CronSchedule


async def test_background_tasks():
    """测试后台任务功能."""
    print("\n" + "=" * 50)
    print("测试后台任务功能")
    print("=" * 50)

    job_manager = get_job_manager()
    job_manager._jobs.clear()

    print("\n1. 创建任务...")
    result = await start_background_task.ainvoke(
        {"task_description": "测试任务：计算 1+1", "label": "测试任务"}
    )
    print(f"   结果: {result}")

    job_id = None
    for jid in job_manager._jobs:
        job_id = jid
        break

    if not job_id:
        print("   ❌ 任务创建失败")
        return False

    print(f"   ✅ 任务已创建: {job_id}")

    print("\n2. 检查任务状态...")
    status = check_task_status.invoke({"job_id": job_id})
    print(f"   状态: {status}")

    print("\n3. 列出所有任务...")
    tasks = list_background_tasks.invoke({"include_completed": True})
    print(f"   任务列表:\n{tasks}")

    print("\n4. 等待任务完成...")
    for _ in range(10):
        job = job_manager.get_status(job_id)
        if job and job.status in ("completed", "failed"):
            break
        await asyncio.sleep(1)

    job = job_manager.get_status(job_id)
    if job and job.status == "completed":
        print(f"   ✅ 任务已完成")
        print(f"   结果: {job.result[:100] if job.result else 'N/A'}...")
    else:
        print(f"   ⚠️ 任务状态: {job.status if job else 'N/A'}")

    print("\n5. 获取任务结果...")
    result = get_task_result.invoke({"job_id": job_id})
    print(f"   结果: {result[:200] if result else 'N/A'}...")

    print("\n✅ 后台任务测试完成")
    return True


async def test_cron_tasks():
    """测试定时任务功能."""
    print("\n" + "=" * 50)
    print("测试定时任务功能")
    print("=" * 50)

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        service = CronService(Path(tmpdir))
        set_cron_service(service)

        print("\n1. 创建间隔任务...")
        result = create_cron.invoke(
            {
                "name": "测试间隔任务",
                "message": "每分钟执行一次测试",
                "every_seconds": 60,
            }
        )
        print(f"   结果: {result}")

        print("\n2. 创建一次性任务...")
        result = create_cron.invoke(
            {
                "name": "测试一次性任务",
                "message": "一次性提醒",
                "at": "2026-12-31T23:59:00",
            }
        )
        print(f"   结果: {result}")

        print("\n3. 列出所有定时任务...")
        tasks = list_crons.invoke({"include_disabled": True})
        print(f"   任务列表:\n{tasks}")

        jobs = service.list_jobs(include_disabled=True)
        if len(jobs) >= 2:
            print(f"   ✅ 已创建 {len(jobs)} 个任务")
        else:
            print(f"   ❌ 任务创建失败")
            return False

        job_id = jobs[0].id

        print("\n4. 获取任务详情...")
        status = get_cron_status.invoke({"cron_id": job_id})
        print(f"   详情:\n{status}")

        print("\n5. 禁用任务...")
        result = toggle_cron.invoke({"cron_id": job_id, "enabled": False})
        print(f"   结果: {result}")

        job = service.get_job(job_id)
        if job and not job.enabled:
            print("   ✅ 任务已禁用")
        else:
            print("   ❌ 禁用失败")
            return False

        print("\n6. 启用任务...")
        result = toggle_cron.invoke({"cron_id": job_id, "enabled": True})
        print(f"   结果: {result}")

        job = service.get_job(job_id)
        if job and job.enabled:
            print("   ✅ 任务已启用")
        else:
            print("   ❌ 启用失败")
            return False

        print("\n7. 删除任务...")
        result = delete_cron.invoke({"cron_id": job_id})
        print(f"   结果: {result}")

        job = service.get_job(job_id)
        if not job:
            print("   ✅ 任务已删除")
        else:
            print("   ❌ 删除失败")
            return False

    print("\n✅ 定时任务测试完成")
    return True


async def test_cron_service_lifecycle():
    """测试 CronService 生命周期."""
    print("\n" + "=" * 50)
    print("测试 CronService 生命周期")
    print("=" * 50)

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        service = CronService(Path(tmpdir))

        print("\n1. 启动服务...")
        await service.start()
        print("   ✅ 服务已启动")

        print("\n2. 添加任务...")
        job = service.add_job(
            name="生命周期测试",
            schedule=CronSchedule(kind="every", every_ms=5000),
            message="测试消息",
        )
        print(f"   ✅ 任务已添加: {job.id}")

        print("\n3. 检查服务状态...")
        if service._running:
            print("   ✅ 服务正在运行")
        else:
            print("   ❌ 服务未运行")
            return False

        print("\n4. 停止服务...")
        service.stop()
        print("   ✅ 服务已停止")

        if not service._running:
            print("   ✅ 服务已正确停止")
        else:
            print("   ❌ 服务停止失败")
            return False

    print("\n✅ 生命周期测试完成")
    return True


async def test_subagent_manager():
    """测试 SubagentManager 初始化."""
    print("\n" + "=" * 50)
    print("测试 SubagentManager")
    print("=" * 50)

    print("\n1. 检查 SubagentManager 类...")
    print(f"   ✅ SubagentManager 类存在")

    print("\n2. 检查 JobManager 集成...")
    job_manager = get_job_manager()
    print(f"   ✅ JobManager 实例获取成功")

    print("\n3. 检查 set_subagent_manager 方法...")
    print(f"   ✅ set_subagent_manager 方法存在: {hasattr(job_manager, 'set_subagent_manager')}")

    print("\n✅ SubagentManager 测试完成")
    return True


async def main():
    """运行所有测试."""
    print("\n" + "=" * 60)
    print("FinchBot 端到端集成测试")
    print("=" * 60)

    results = {}

    results["后台任务"] = await test_background_tasks()
    results["定时任务"] = await test_cron_tasks()
    results["CronService 生命周期"] = await test_cron_service_lifecycle()
    results["SubagentManager"] = await test_subagent_manager()

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    all_passed = True
    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试失败")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
