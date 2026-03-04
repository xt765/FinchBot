"""子代理管理器.

参考 nanobot 设计，实现真正的后台子代理执行：
- 独立的 agent loop
- 完整的工具集配置
- 结果通知机制
- 会话级任务管理
- 迭代限制
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from loguru import logger

from finchbot.i18n import t

if TYPE_CHECKING:
    from finchbot.config.schema import Config


def _get_tool_name(tool: BaseTool) -> str:
    """安全获取工具名称.

    Args:
        tool: 工具实例

    Returns:
        工具名称
    """
    return getattr(tool, "name", str(tool))


class SubagentManager:
    """子代理管理器.

    管理后台子代理的创建、执行和结果通知。

    Attributes:
        model: 语言模型实例
        workspace: 工作目录
        tools: 可用工具列表
        config: 配置对象
        on_notify: 结果通知回调
        max_iterations: 最大迭代次数
        _running_tasks: 运行中的任务映射
        _session_tasks: 会话级任务映射
    """

    def __init__(
        self,
        model: BaseChatModel,
        workspace: Path,
        tools: list[BaseTool],
        config: Config | None = None,
        on_notify: Callable[[str, str, str], Any] | None = None,
        max_iterations: int = 15,
    ) -> None:
        """初始化子代理管理器.

        Args:
            model: 语言模型实例
            workspace: 工作目录
            tools: 可用工具列表（子代理可用）
            config: 配置对象
            on_notify: 结果通知回调 (session_key, label, result)
            max_iterations: 最大迭代次数
        """
        self.model = model
        self.workspace = workspace
        self.tools = tools
        self.config = config
        self.on_notify = on_notify
        self.max_iterations = max_iterations
        self._running_tasks: dict[str, asyncio.Task[str]] = {}
        self._session_tasks: dict[str, set[str]] = {}
        self._task_results: dict[str, str] = {}

    async def spawn(
        self,
        task: str,
        label: str | None = None,
        session_key: str = "cli:default",
    ) -> str:
        """启动子代理执行后台任务.

        Args:
            task: 任务描述
            label: 任务标签（用于显示）
            session_key: 会话标识

        Returns:
            启动信息
        """
        task_id = str(uuid.uuid4())[:8]
        display_label = label or (task[:30] + "..." if len(task) > 30 else task)

        bg_task = asyncio.create_task(self._run_subagent(task_id, task, display_label, session_key))
        self._running_tasks[task_id] = bg_task
        self._session_tasks.setdefault(session_key, set()).add(task_id)

        def _cleanup(_: asyncio.Task) -> None:
            self._running_tasks.pop(task_id, None)
            if session_key and (ids := self._session_tasks.get(session_key)):
                ids.discard(task_id)
                if not ids:
                    del self._session_tasks[session_key]

        bg_task.add_done_callback(_cleanup)

        logger.info(f"Subagent [{task_id}] started: {display_label}")
        return t("background.task_started", job_id=task_id) + f" ({display_label})"

    async def _run_subagent(
        self,
        task_id: str,
        task: str,
        label: str,
        session_key: str,
    ) -> str:
        """执行子代理任务.

        Args:
            task_id: 任务 ID
            task: 任务描述
            label: 任务标签
            session_key: 会话标识

        Returns:
            执行结果
        """
        logger.info(f"Subagent [{task_id}] starting task: {label}")

        try:
            system_prompt = self._build_subagent_prompt()
            messages: list[Any] = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=task),
            ]

            bound_model = self.model.bind_tools(self.tools) if self.tools else self.model

            iteration = 0
            final_result: str | None = None

            while iteration < self.max_iterations:
                iteration += 1

                response = await bound_model.ainvoke(messages)

                if isinstance(response, AIMessage):
                    messages.append(response)

                    if response.tool_calls:
                        for tool_call in response.tool_calls:
                            result = await self._execute_tool(dict(tool_call))
                            messages.append(
                                ToolMessage(
                                    content=result,
                                    tool_call_id=tool_call["id"],
                                )
                            )
                    else:
                        content = response.content
                        final_result = str(content) if content else ""
                        break
                else:
                    final_result = (
                        str(response.content) if hasattr(response, "content") else str(response)
                    )
                    break

            if final_result is None:
                final_result = "Task completed but no final response was generated."

            logger.info(f"Subagent [{task_id}] completed successfully")
            await self._announce_result(task_id, label, task, final_result, session_key, "ok")
            return final_result

        except asyncio.CancelledError:
            logger.info(f"Subagent [{task_id}] cancelled")
            await self._announce_result(
                task_id, label, task, "Task cancelled", session_key, "cancelled"
            )
            return "Task cancelled"

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(f"Subagent [{task_id}] failed: {e}")
            await self._announce_result(task_id, label, task, error_msg, session_key, "error")
            return error_msg

    async def _execute_tool(self, tool_call: dict) -> str:
        """执行工具调用.

        Args:
            tool_call: 工具调用信息

        Returns:
            执行结果
        """
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {})

        for tool in self.tools:
            if tool.name == tool_name:
                try:
                    result = await tool.ainvoke(tool_args)
                    return str(result)
                except Exception as e:
                    return f"Tool error: {e}"

        return f"Tool not found: {tool_name}"

    async def _announce_result(
        self,
        task_id: str,
        label: str,
        task: str,
        result: str,
        session_key: str,
        status: str,
    ) -> None:
        """通知子代理执行结果.

        Args:
            task_id: 任务 ID
            label: 任务标签
            task: 任务描述
            result: 执行结果
            session_key: 会话标识
            status: 执行状态
        """
        status_text = (
            t("background.status.completed") if status == "ok" else t("background.status.failed")
        )

        announce_content = f"""[Subagent '{label}' {status_text}]

Task: {task}

Result:
{result}

Summarize this naturally for the user. Keep it brief (1-2 sentences). Do not mention technical details like "subagent" or task IDs."""

        if self.on_notify:
            try:
                import asyncio

                if asyncio.iscoroutinefunction(self.on_notify):
                    await self.on_notify(session_key, label, announce_content)
                else:
                    self.on_notify(session_key, label, announce_content)
            except Exception as e:
                logger.error(f"Failed to notify subagent result: {e}")

    def _build_subagent_prompt(self) -> str:
        """构建子代理系统提示.

        Returns:
            系统提示字符串
        """
        import platform
        from datetime import datetime

        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        runtime = f"{platform.system()} {platform.machine()}, Python {platform.python_version()}"

        parts = [
            f"""# Subagent

## Runtime
{now}
{runtime}

## Workspace
{self.workspace}

You are a subagent spawned by the main agent to complete a specific task.
Stay focused on the assigned task. Your final response will be reported back to the main agent.

## Guidelines
- Complete the task efficiently
- Use available tools as needed
- Provide a clear summary when done
- Do not mention technical details like "subagent" or task IDs in your final response""",
        ]

        return "\n\n".join(parts)

    async def cancel_by_session(self, session_key: str) -> int:
        """取消指定会话的所有子代理任务.

        Args:
            session_key: 会话标识

        Returns:
            取消的任务数量
        """
        task_ids = self._session_tasks.get(session_key, set())
        tasks = [
            self._running_tasks[tid]
            for tid in task_ids
            if tid in self._running_tasks and not self._running_tasks[tid].done()
        ]

        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        return len(tasks)

    def cancel_task(self, task_id: str) -> bool:
        """取消指定任务.

        Args:
            task_id: 任务 ID

        Returns:
            是否成功取消
        """
        if task_id in self._running_tasks:
            task = self._running_tasks[task_id]
            if not task.done():
                task.cancel()
                return True
        return False

    def get_running_count(self) -> int:
        """获取运行中的任务数量.

        Returns:
            任务数量
        """
        return len([t for t in self._running_tasks.values() if not t.done()])

    def get_task_ids(self) -> list[str]:
        """获取所有任务 ID.

        Returns:
            任务 ID 列表
        """
        return list(self._running_tasks.keys())

    def get_session_task_ids(self, session_key: str) -> list[str]:
        """获取指定会话的任务 ID.

        Args:
            session_key: 会话标识

        Returns:
            任务 ID 列表
        """
        return list(self._session_tasks.get(session_key, set()))

    def update_tools(self, new_tools: list[BaseTool]) -> None:
        """更新工具列表.

        当 MCP 工具热更新时调用。
        新创建的子代理将使用新的工具列表。

        Args:
            new_tools: 新的工具列表
        """
        self.tools = new_tools
        logger.info(f"SubagentManager 工具已更新: {len(new_tools)} 个工具")

        for task_id, task in self._running_tasks.items():
            if not task.done():
                logger.debug(f"子代理 {task_id} 将在下次迭代使用新工具")

    async def cancel_all(self) -> int:
        """取消所有运行中的任务.

        Returns:
            取消的任务数量
        """
        tasks = [task for task in self._running_tasks.values() if not task.done()]

        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        return len(tasks)

    async def spawn_and_wait(
        self,
        task: str,
        label: str | None = None,
        session_key: str = "cli:default",
    ) -> str:
        """启动子代理并返回任务 ID（不等待结果）.

        Args:
            task: 任务描述
            label: 任务标签
            session_key: 会话标识

        Returns:
            任务 ID
        """
        task_id = str(uuid.uuid4())[:8]
        display_label = label or (task[:30] + "..." if len(task) > 30 else task)

        bg_task = asyncio.create_task(self._run_subagent(task_id, task, display_label, session_key))
        self._running_tasks[task_id] = bg_task
        self._session_tasks.setdefault(session_key, set()).add(task_id)

        def _cleanup(t: asyncio.Task) -> None:
            self._running_tasks.pop(task_id, None)
            if session_key and (ids := self._session_tasks.get(session_key)):
                ids.discard(task_id)
                if not ids:
                    del self._session_tasks[session_key]

            try:
                result = t.result()
                self._task_results[task_id] = result or "Task completed"
            except Exception as e:
                self._task_results[task_id] = f"Task failed: {e}"

        bg_task.add_done_callback(_cleanup)

        logger.info(f"Subagent [{task_id}] started: {display_label}")
        return task_id

    async def wait_for_result(self, task_id: str, timeout: float = 300) -> str | None:
        """等待任务完成并返回结果.

        Args:
            task_id: 任务 ID
            timeout: 超时时间（秒）

        Returns:
            任务结果，超时返回 None
        """
        if task_id not in self._running_tasks:
            return self._task_results.get(task_id)

        task = self._running_tasks.get(task_id)
        if not task:
            return self._task_results.get(task_id)

        try:
            await asyncio.wait_for(task, timeout=timeout)
            return self._task_results.get(task_id)
        except TimeoutError:
            logger.warning(f"Task {task_id} timed out after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            return self._task_results.get(task_id)
