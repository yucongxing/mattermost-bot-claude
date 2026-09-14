from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path

from app.models import ExecutionResult


class Executor(ABC):
    @abstractmethod
    async def execute(self, prompt: str, cwd: Path, timeout: int) -> ExecutionResult:
        raise NotImplementedError


async def run_process(
    *argv: str,
    cwd: Path,
    timeout: int,
) -> ExecutionResult:
    proc = await asyncio.create_subprocess_exec(
        *argv,
        cwd=str(cwd),
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        return ExecutionResult(
            returncode=124,
            stdout="",
            stderr=f"task timed out after {timeout} seconds",
        )

    return ExecutionResult(
        returncode=proc.returncode or 0,
        stdout=stdout_b.decode("utf-8", errors="replace"),
        stderr=stderr_b.decode("utf-8", errors="replace"),
    )
