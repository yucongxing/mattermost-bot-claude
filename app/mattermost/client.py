from __future__ import annotations

import httpx

from app.config import Settings


class MattermostClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=f"{settings.mattermost_url}/api/v4",
            headers={"Authorization": f"Bearer {settings.mattermost_bot_token}"},
            verify=settings.mattermost_verify_tls,
            timeout=httpx.Timeout(30.0),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get_me(self) -> dict:
        response = await self._client.get("/users/me")
        response.raise_for_status()
        return response.json()

    async def create_post(
        self,
        channel_id: str,
        message: str,
        *,
        root_id: str | None = None,
    ) -> dict:
        payload: dict[str, str] = {
            "channel_id": channel_id,
            "message": message,
        }
        if root_id:
            payload["root_id"] = root_id

        response = await self._client.post("/posts", json=payload)
        response.raise_for_status()
        return response.json()
