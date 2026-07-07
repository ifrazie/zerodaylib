"""Tests for backend/db/seed_embed.py — the idempotent Titan embedding refresh.

These tests mock the Bedrock client and a minimal DB connection/cursor, so
they run offline without COCKROACH_URL or AWS credentials. Live-DB coverage
(seeding real embeddings end-to-end) is exercised manually via
`python -m backend.db.seed_embed` and validated by the memory_search_similar
tests in test_tools.py once run against a live cluster.
"""
import json

import backend.db.seed_embed as seed_embed


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


class FakeBedrockClient:
    def __init__(self):
        self.calls = []

    def invoke_model(self, **kwargs):
        self.calls.append(kwargs)
        return {"body": FakeResponse({"embedding": [0.1, 0.2]})}


class FakeCursor:
    def __init__(self, unembedded_rows):
        self._unembedded_rows = unembedded_rows
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return self._unembedded_rows


class FakeConn:
    def __init__(self, unembedded_rows):
        self._cursor = FakeCursor(unembedded_rows)

    def cursor(self):
        return self._cursor


# --- embed_texts ----------------------------------------------------------


def test_embed_texts_uses_single_input_text_payload(monkeypatch):
    fake_client = FakeBedrockClient()
    monkeypatch.setattr(seed_embed, "_get_bedrock_client", lambda: fake_client)

    result = seed_embed.embed_texts(["hello world"])

    assert result == [[0.1, 0.2]]
    assert len(fake_client.calls) == 1
    body = json.loads(fake_client.calls[0]["body"])
    assert body["inputText"] == "hello world"
    assert "inputTexts" not in body
    assert body["dimensions"] == seed_embed.EMBED_DIM
    assert body["normalize"] is True


def test_embed_texts_embeds_each_text_independently(monkeypatch):
    fake_client = FakeBedrockClient()
    monkeypatch.setattr(seed_embed, "_get_bedrock_client", lambda: fake_client)
    monkeypatch.setattr(seed_embed.time, "sleep", lambda *_: None)

    result = seed_embed.embed_texts(["first", "second", "third"])

    assert len(result) == 3
    assert len(fake_client.calls) == 3


# --- _vector_literal --------------------------------------------------------


def test_vector_literal_format():
    literal = seed_embed._vector_literal([0.1, 0.25, -0.5])
    assert literal == "[0.10000000,0.25000000,-0.50000000]"
    assert literal.startswith("[") and literal.endswith("]")


# --- embed_unembedded_rows: idempotency -------------------------------------


def test_embed_unembedded_rows_noop_when_nothing_unembedded(monkeypatch):
    conn = FakeConn(unembedded_rows=[])
    updated = seed_embed.embed_unembedded_rows(conn)
    assert updated == 0
    # Only the SELECT ran; no UPDATE statements were issued.
    assert len(conn._cursor.executed) == 1


def test_embed_unembedded_rows_embeds_and_stamps_embedded_at(monkeypatch):
    fake_client = FakeBedrockClient()
    monkeypatch.setattr(seed_embed, "_get_bedrock_client", lambda: fake_client)
    monkeypatch.setattr(seed_embed.time, "sleep", lambda *_: None)

    rows = [("mem-1", "summary one"), ("mem-2", "summary two")]
    conn = FakeConn(unembedded_rows=rows)

    updated = seed_embed.embed_unembedded_rows(conn)

    assert updated == 2
    # executed[0] is the SELECT; the rest are per-row UPDATEs.
    update_calls = conn._cursor.executed[1:]
    assert len(update_calls) == 2
    updated_ids = {params[1] for _sql, params in update_calls}
    assert updated_ids == {"mem-1", "mem-2"}
    for sql, params in update_calls:
        assert "embedded_at = now()" in sql
        assert "embedding = %s::VECTOR(1024)" in sql
        assert params[0] == seed_embed._vector_literal([0.1, 0.2])
