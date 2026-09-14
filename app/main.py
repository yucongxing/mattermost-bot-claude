from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings
from app.service import AgentGatewayService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

settings = Settings()
service = AgentGatewayService(settings)
listener_task: asyncio.Task[None] | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    global listener_task
    await service.startup()
    listener_task = asyncio.create_task(service.listener.run_forever())
    try:
        yield
    finally:
        service.listener.stop()
        if listener_task:
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                pass
        await service.shutdown()


app = FastAPI(title="Mattermost Agent Gateway", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tasks")
async def tasks() -> list[dict]:
    return service.task_manager.snapshot()
