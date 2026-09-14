from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.config import Settings
from app.executors.base import Executor
from app.mattermost.client import MattermostClient
from app.models import MentionTask, TaskStatus

logger = logging.getLogger(__name__)


class TaskManager:
    def __init__(
        self,
        settings: Settings,
        mattermost: MattermostClient,
        executors: dict[str, Executor],
    ) -> None:
        self.settings = settings
        self.mattermost = mattermost
        self.executors = executors
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_tasks)
        self._active: dict[str, asyncio.Task[None]] = {}
        self._state: dict[str, dict[str, Any]] = {}

    def snapshot(self) -> list[dict[str, Any]]:
        return list(self._state.values())

    def submit(self, task: MentionTask) -> None:
        self._state[task.task_id] = {
            **asdict(task),
            "status": TaskStatus.QUEUED,
        }
        future = asyncio.create_task(self._run(task), name=f"agent-task-{task.task_id}")
        self._active[task.task_id] = future
        future.add_done_callback(lambda _: self._active.pop(task.task_id, None))

    async def _run(self, task: MentionTask) -> None:
        async with self._semaphore:
            self._state[task.task_id]["status"] = TaskStatus.RUNNING
            try:
                result = await self.executors[task.executor].execute(
                    task.prompt,
                    Path(self.settings.agent_workdir),
                    self.settings.task_timeout_seconds,
                )

                if result.ok:
                    self._state[task.task_id]["status"] = TaskStatus.SUCCEEDED
                    body = result.stdout.strip() or "任务执行完成，无标准输出。"
                    await self._reply_long(
                        task,
                        f"✅ `{task.task_id}` 完成（{task.executor}）\n\n{body}",
                    )
                else:
                    self._state[task.task_id]["status"] = TaskStatus.FAILED
                    detail = (result.stderr or result.stdout).strip()
                    await self._reply_long(
                        task,
                        f"❌ `{task.task_id}` 执行失败（exit={result.returncode}）\n\n```text\n{detail}\n```",
                    )
            except Exception as exc:
                logger.exception("Task %s failed", task.task_id)
                self._state[task.task_id]["status"] = TaskStatus.FAILED
                await self.mattermost.create_post(
                    task.channel_id,
                    f"❌ `{task.task_id}` 网关异常：`{type(exc).__name__}: {exc}`",
                    root_id=task.root_id,
                )

    async def _reply_long(self, task: MentionTask, text: str) -> None:
        chunks = _chunk_text(text, self.settings.max_reply_chars)
        for index, chunk in enumerate(chunks, start=1):
            prefix = "" if len(chunks) == 1 else f"[{index}/{len(chunks)}]\n"
            await self.mattermost.create_post(
                task.channel_id,
                prefix + chunk,
                root_id=task.root_id,
            )


def _chunk_text(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit)
        if split_at < limit // 2:
            split_at = limit
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip("\n")
    if remaining:
        chunks.append(remaining)
    return chunks
