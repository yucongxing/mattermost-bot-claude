from __future__ import annotations

import asyncio
import json
import logging
import ssl
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit, urlunsplit

import websockets

from app.config import Settings

logger = logging.getLogger(__name__)

EventHandler = Callable[[dict], Awaitable[None]]


class MattermostWebSocketListener:
    def __init__(self, settings: Settings, handler: EventHandler) -> None:
        self.settings = settings
        self.handler = handler
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    def _websocket_url(self) -> str:
        parsed = urlsplit(self.settings.mattermost_url)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        return urlunsplit((scheme, parsed.netloc, "/api/v4/websocket", "", ""))

    def _ssl_context(self) -> ssl.SSLContext | None:
        if not self._websocket_url().startswith("wss://"):
            return None
        context = ssl.create_default_context()
        if not self.settings.mattermost_verify_tls:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return context

    async def run_forever(self) -> None:
        delay = 1
        while not self._stop.is_set():
            try:
                await self._run_once()
                delay = 1
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Mattermost websocket disconnected")
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=delay)
                except TimeoutError:
                    pass
                delay = min(delay * 2, 30)

    async def _run_once(self) -> None:
        url = self._websocket_url()
        logger.info("Connecting Mattermost websocket: %s", url)

        async with websockets.connect(
            url,
            ssl=self._ssl_context(),
            ping_interval=20,
            ping_timeout=20,
            close_timeout=10,
            max_size=2**20,
        ) as ws:
            await ws.send(
                json.dumps(
                    {
                        "seq": 1,
                        "action": "authentication_challenge",
                        "data": {"token": self.settings.mattermost_bot_token},
                    }
                )
            )

            async for raw in ws:
                if self._stop.is_set():
                    return
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("Ignored invalid websocket JSON")
                    continue

                await self.handler(event)
