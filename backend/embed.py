"""
backend/embed.py — Shared Bedrock Titan Text v2 embedding helper.

Single source of truth for turning text into a 1024-dim embedding vector,
imported by both the FastAPI service (backend/main.py) and the Lambda gateway
handler (backend/lambda_handler.py) so query-side and write-side embedding
behave identically. Kept dependency-light: boto3 is imported lazily so modules
that only need the tool contracts can import this without a hard boto3 dep.

Requires AWS credentials with bedrock:InvokeModel on
amazon.titan-embed-text-v2:0.
"""
from __future__ import annotations

import json
import os

EMBED_MODEL_ID = "amazon.titan-embed-text-v2:0"
EMBED_DIM = 1024
MAX_TEXT_LEN = 8192

_bedrock_runtime = None


def _get_bedrock_runtime():
    """Lazily create and cache the Bedrock runtime client."""
    global _bedrock_runtime
    if _bedrock_runtime is None:
        import boto3

        region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        _bedrock_runtime = boto3.client("bedrock-runtime", region_name=region)
    return _bedrock_runtime


def embed_text(text: str) -> list[float]:
    """Embed a single text string with Bedrock Titan Text v2 → 1024-dim floats.

    Uses dimensions=1024 and normalize=True so vectors are unit-length and
    directly comparable via L2 distance in CockroachDB's vector index.
    """
    client = _get_bedrock_runtime()
    resp = client.invoke_model(
        modelId=EMBED_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(
            {
                "inputText": text[:MAX_TEXT_LEN],
                "dimensions": EMBED_DIM,
                "normalize": True,
            }
        ),
    )
    payload = json.loads(resp["body"].read())
    return payload["embedding"]
