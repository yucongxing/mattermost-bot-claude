from __future__ import annotations

import logging
import uuid

from app.config import Settings
from app.executors import ClaudeExecutor, CodexExecutor, LocalLLMExecutor
from app.mattermost.client import MattermostClient
from app.mattermost.parser import extract_mention_prompt, parse_posted_event, select_executor
from app.mattermost.websocket_listener import MattermostWebSocketListener
from app.models import MentionTask
from app.task_manager import TaskManager

logger = logging.getLogger(__name__)


class AgentGatewayService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.mattermost = MattermostClient(settings)
        self.bot_user_id: str | None = None
        self.task_manager = TaskManager(
            settings,
            self.mattermost,
            {
                "codex": CodexExecutor(settings.codex_bin),
                "claude": ClaudeExecutor(settings.claude_bin),
                "local_llm": LocalLLMExecutor(
                    base_url=settings.local_llm_base_url,
                    api_key=settings.local_llm_api_key,
                    model=settings.local_llm_model,
                ),
            },
        )
        self.listener = MattermostWebSocketListener(settings, self.handle_event)

    async def startup(self) -> None:
        me = await self.mattermost.get_me()
        self.bot_user_id = me["id"]
        actual_username = me.get("username")
        if actual_username and actual_username != self.settings.mattermost_bot_username:
            logger.warning(
                "Configured bot username=%s, Mattermost says username=%s",
                self.settings.mattermost_bot_username,
                actual_username,
            )
        logger.info("Authenticated Mattermost bot: %s (%s)", actual_username, self.bot_user_id)

    async def shutdown(self) -> None:
        self.listener.stop()
        await self.mattermost.close()

    async def handle_event(self, event: dict) -> None:
        post = parse_posted_event(event)
        if not post:
            return

        if self.bot_user_id and post.get("user_id") == self.bot_user_id:
            return

        message = post.get("message") or ""
        prompt = extract_mention_prompt(message, self.settings.mattermost_bot_username)
        if prompt is None:
            return

        channel_id = post.get("channel_id")
        source_post_id = post.get("id")
        user_id = post.get("user_id")
        if not all((channel_id, source_post_id, user_id)):
            logger.warning("Ignoring incomplete post event: %s", post)
            return

        root_id = post.get("root_id") or source_post_id

        if not prompt:
            await self.mattermost.create_post(
                channel_id,
                "请在 @ 后面写任务，例如：`@dev-agent codex: 检查当前项目的内存泄漏风险`。",
                root_id=root_id,
            )
            return

        executor, clean_prompt = select_executor(prompt, self.settings.default_executor)
        task_id = f"TASK-{uuid.uuid4().hex[:8].upper()}"

        task = MentionTask(
            task_id=task_id,
            channel_id=channel_id,
            source_post_id=source_post_id,
            root_id=root_id,
            user_id=user_id,
            prompt=clean_prompt,
            executor=executor,
        )

        await self.mattermost.create_post(
            channel_id,
            f"🟡 `{task_id}` 已接收，执行器：`{executor}`。",
            root_id=root_id,
        )
        self.task_manager.submit(task)
