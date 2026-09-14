from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ExecutorName = Literal["codex", "claude", "local_llm"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    mattermost_url: str
    mattermost_bot_token: str
    mattermost_bot_username: str = "dev-agent"
    mattermost_verify_tls: bool = True

    default_executor: ExecutorName = "codex"
    agent_workdir: Path = Path(".")

    task_timeout_seconds: int = Field(default=1800, ge=10)
    max_concurrent_tasks: int = Field(default=2, ge=1, le=32)
    max_reply_chars: int = Field(default=12000, ge=1000, le=60000)

    codex_bin: str = "codex"
    claude_bin: str = "claude"

    local_llm_base_url: str = "http://127.0.0.1:8000/v1"
    local_llm_api_key: str = "local"
    local_llm_model: str = "qwen3"

    @field_validator("mattermost_url")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("agent_workdir")
    @classmethod
    def normalize_workdir(cls, value: Path) -> Path:
        return value.expanduser().resolve()
