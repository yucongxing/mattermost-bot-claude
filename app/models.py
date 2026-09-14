from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


ExecutorName = Literal["codex", "claude", "local_llm"]


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(slots=True)
class MentionTask:
    task_id: str
    channel_id: str
    source_post_id: str
    root_id: str
    user_id: str
    prompt: str
    executor: ExecutorName


@dataclass(slots=True)
class ExecutionResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0
