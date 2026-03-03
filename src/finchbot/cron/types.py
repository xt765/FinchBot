"""定时任务类型定义.

参考 nanobot 设计，支持三种调度模式：
- at: 一次性任务（指定时间戳）
- every: 间隔任务（毫秒级）
- cron: cron 表达式（支持时区）
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal


def now_ms() -> int:
    """获取当前时间戳（毫秒）."""
    return int(time.time() * 1000)


@dataclass
class CronSchedule:
    """调度定义.

    支持三种调度模式：
    - at: 一次性任务，在指定时间执行一次
    - every: 间隔任务，按固定间隔重复执行
    - cron: cron 表达式，按复杂时间规则执行

    Attributes:
        kind: 调度类型 (at/every/cron)
        at_ms: 一次性任务的执行时间戳（毫秒）
        every_ms: 间隔任务的间隔时间（毫秒）
        expr: cron 表达式（如 "0 9 * * *"）
        tz: IANA 时区名称（如 "Asia/Shanghai"）
    """

    kind: Literal["at", "every", "cron"]
    at_ms: int | None = None
    every_ms: int | None = None
    expr: str | None = None
    tz: str | None = None

    def validate(self) -> None:
        """验证调度配置的有效性."""
        if self.kind == "at" and not self.at_ms:
            raise ValueError("at_ms is required for 'at' schedule")
        if self.kind == "every" and not self.every_ms:
            raise ValueError("every_ms is required for 'every' schedule")
        if self.kind == "cron" and not self.expr:
            raise ValueError("expr is required for 'cron' schedule")
        if self.tz and self.kind != "cron":
            raise ValueError("tz can only be used with 'cron' schedule")
        if self.tz:
            from zoneinfo import ZoneInfo

            try:
                ZoneInfo(self.tz)
            except Exception as e:
                raise ValueError(f"Invalid timezone '{self.tz}': {e}") from e


@dataclass
class CronPayload:
    """任务载荷.

    定义任务执行时的行为和投递方式。

    Attributes:
        kind: 载荷类型 (system_event/agent_turn)
        message: 任务消息内容
        deliver: 是否投递响应到渠道
        channel: 投递渠道名称（如 telegram, discord）
        to: 投递目标标识（如聊天 ID）
    """

    kind: Literal["system_event", "agent_turn"] = "agent_turn"
    message: str = ""
    deliver: bool = False
    channel: str | None = None
    to: str | None = None


@dataclass
class CronJobState:
    """任务运行状态.

    跟踪任务的执行历史和下次执行时间。

    Attributes:
        next_run_at_ms: 下次执行时间戳（毫秒）
        last_run_at_ms: 上次执行时间戳（毫秒）
        last_status: 上次执行状态 (ok/error/skipped)
        last_error: 上次执行错误信息
    """

    next_run_at_ms: int | None = None
    last_run_at_ms: int | None = None
    last_status: Literal["ok", "error", "skipped"] | None = None
    last_error: str | None = None


@dataclass
class CronJob:
    """定时任务.

    完整的定时任务定义，包含调度、载荷和状态。

    Attributes:
        id: 任务唯一标识
        name: 任务名称
        enabled: 是否启用
        schedule: 调度配置
        payload: 任务载荷
        state: 运行状态
        created_at_ms: 创建时间戳（毫秒）
        updated_at_ms: 更新时间戳（毫秒）
        delete_after_run: 执行后是否删除（用于一次性任务）
    """

    id: str
    name: str
    enabled: bool = True
    schedule: CronSchedule = field(default_factory=lambda: CronSchedule(kind="every"))
    payload: CronPayload = field(default_factory=CronPayload)
    state: CronJobState = field(default_factory=CronJobState)
    created_at_ms: int = 0
    updated_at_ms: int = 0
    delete_after_run: bool = False


@dataclass
class CronStore:
    """任务存储.

    持久化存储所有定时任务。

    Attributes:
        version: 存储格式版本
        jobs: 任务列表
    """

    version: int = 1
    jobs: list[CronJob] = field(default_factory=list)
