from __future__ import annotations

from pathlib import Path

from app.executors.base import Executor, run_process
from app.models import ExecutionResult


class ClaudeExecutor(Executor):
    def __init__(self, binary: str = "claude") -> None:
        self.binary = binary

    async def execute(self, prompt: str, cwd: Path, timeout: int) -> ExecutionResult:
        return await run_process(
            self.binary,
            "-p",
            prompt,
            "--output-format",
            "text",
            cwd=cwd,
            timeout=timeout,
        )
