from __future__ import annotations

from pathlib import Path

from app.executors.base import Executor, run_process
from app.models import ExecutionResult


class CodexExecutor(Executor):
    def __init__(self, binary: str = "codex") -> None:
        self.binary = binary

    async def execute(self, prompt: str, cwd: Path, timeout: int) -> ExecutionResult:
        return await run_process(
            self.binary,
            "exec",
            prompt,
            cwd=cwd,
            timeout=timeout,
        )
