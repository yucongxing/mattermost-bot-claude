from app.task_manager import _chunk_text


def test_chunk_text_short():
    assert _chunk_text("abc", 10) == ["abc"]


def test_chunk_text_long():
    chunks = _chunk_text("a" * 25, 10)
    assert chunks == ["a" * 10, "a" * 10, "a" * 5]
