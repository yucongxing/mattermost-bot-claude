import json

from app.mattermost.parser import extract_mention_prompt, parse_posted_event, select_executor


def test_parse_posted_event_string_post():
    payload = {
        "event": "posted",
        "data": {"post": json.dumps({"id": "p1", "message": "hello"})},
    }
    assert parse_posted_event(payload) == {"id": "p1", "message": "hello"}


def test_extract_mention_prompt():
    assert (
        extract_mention_prompt("@dev-agent codex: check parser", "dev-agent")
        == "codex: check parser"
    )
    assert extract_mention_prompt("hello", "dev-agent") is None


def test_select_executor_prefix():
    assert select_executor("claude: review this", "codex") == ("claude", "review this")
    assert select_executor("llm: explain vector", "codex") == ("local_llm", "explain vector")
    assert select_executor("fix bug", "codex") == ("codex", "fix bug")
