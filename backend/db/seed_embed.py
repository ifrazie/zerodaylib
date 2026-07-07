"""
backend/db/seed_embed.py — Idempotent Titan embedding refresh for semantic_memory.

Embeds every semantic_memory row where embedded_at IS NULL using Bedrock Titan
Text Embeddings v2 (1024-dim, normalized), then stamps embedded_at = now() on
each updated row.

This replaces the old backend/embed_titan.py, which re-embedded every row on
every run. This module only touches unembedded rows, so it is safe to call on
every dev startup (scripts/dev.sh / scripts/dev.ps1) or CI run without
re-hitting Bedrock for rows that already carry a real vector.

Usage:
    python -m backend.db.seed_embed

Requires:
    COCKROACH_URL — CockroachDB connection string (see backend/tools/db.py)
    AWS credentials with bedrock:InvokeModel on amazon.titan-embed-text-v2:0
"""
from __future__ import annotations

import json
import time
from typing import Any

import boto3
import psycopg

from backend.tools.db import get_psycopg_conn

EMBED_MODEL_ID = "amazon.titan-embed-text-v2:0"
EMBED_DIM = 1024
MAX_TEXT_LEN = 8192
_INTER_CALL_SLEEP_SECONDS = 0.1

_bedrock_client = None


def _get_bedrock_client():
    """Lazily create the Bedrock runtime client (mockable in tests)."""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client(service_name="bedrock-runtime", region_name="us-east-1")
    return _bedrock_client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts via Bedrock Titan Text v2 (1024-dim, normalized)."""
    client = _get_bedrock_client()
    vectors: list[list[float]] = []
    for index, text in enumerate(texts):
        body = {
            "inputText": text[:MAX_TEXT_LEN],
            "dimensions": EMBED_DIM,
            "normalize": True,
        }
        resp = client.invoke_model(
            modelId=EMBED_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        payload = json.loads(resp["body"].read())
        vectors.append(payload["embedding"])
        if index + 1 < len(texts):
            time.sleep(_INTER_CALL_SLEEP_SECONDS)
    return vectors


def _vector_literal(vec: list[float]) -> str:
    """Render a float list as a pgvector-compatible literal string, e.g. '[0.1,0.2]'."""
    return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"


def embed_unembedded_rows(conn: psycopg.Connection[Any]) -> int:
    """
    Embed every semantic_memory row where embedded_at IS NULL.

    Idempotent: rows that already carry a real embedding (embedded_at set) are
    left untouched, so this is safe to call on every app startup.

    Returns the number of rows updated.
    """
    cur = conn.cursor()
    cur.execute("SELECT memory_id, summary FROM semantic_memory WHERE embedded_at IS NULL")
    rows = cur.fetchall()
    if not rows:
        return 0

    texts = [row[1] for row in rows]
    vectors = embed_texts(texts)

    for (memory_id, _summary), vector in zip(rows, vectors):
        cur.execute(
            "UPDATE semantic_memory SET embedding = %s::VECTOR(1024), embedded_at = now() "
            "WHERE memory_id = %s",
            (_vector_literal(vector), str(memory_id)),
        )
    return len(rows)


def refresh_memory_vectors() -> None:
    """CLI entry point: embed all unembedded semantic_memory rows."""
    conn = get_psycopg_conn()
    try:
        updated = embed_unembedded_rows(conn)
        if updated:
            print(f"Embedded {updated} semantic_memory row(s) with real Titan vectors.")
        else:
            print("No unembedded semantic_memory rows found; nothing to do.")
    finally:
        conn.close()


if __name__ == "__main__":
    refresh_memory_vectors()
