from __future__ import annotations

from pathlib import Path

import httpx

from app.executors.base import Executor
from app.models import ExecutionResult


class LocalLLMExecutor(Executor):
    def __init__(self, *, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def execute(self, prompt: str, cwd: Path, timeout: int) -> ExecutionResult:
        del cwd
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2,
                    },
                )
                response.raise_for_status()
                data = response.json()
                text = data["choices"][0]["message"]["content"]
                return ExecutionResult(returncode=0, stdout=text, stderr="")
        except Exception as exc:
            return ExecutionResult(returncode=1, stdout="", stderr=str(exc))
