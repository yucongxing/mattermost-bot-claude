from __future__ import annotations

import json
import re
from typing import Any

from app.models import ExecutorName


def parse_posted_event(payload: dict[str, Any]) -> dict[str, Any] | None:
    if payload.get("event") != "posted":
        return None

    raw_post = payload.get("data", {}).get("post")
    if not raw_post:
        return None

    if isinstance(raw_post, str):
        try:
            return json.loads(raw_post)
        except json.JSONDecodeError:
            return None

    if isinstance(raw_post, dict):
        return raw_post

    return None


def extract_mention_prompt(message: str, bot_username: str) -> str | None:
    pattern = re.compile(rf"(?<!\w)@{re.escape(bot_username)}\b", re.IGNORECASE)
    if not pattern.search(message):
        return None

    cleaned = pattern.sub(" ", message)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def select_executor(prompt: str, default: ExecutorName) -> tuple[ExecutorName, str]:
    prefixes: tuple[tuple[str, ExecutorName], ...] = (
        ("codex:", "codex"),
        ("claude:", "claude"),
        ("llm:", "local_llm"),
    )

    lowered = prompt.lower()
    for prefix, executor in prefixes:
        if lowered.startswith(prefix):
            return executor, prompt[len(prefix):].lstrip()

    return default, prompt
