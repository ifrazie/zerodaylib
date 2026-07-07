"""
Tool: memory_store

Write a new prior-incident memory into semantic_memory with a real Titan
embedding, closing the RAG loop so that resolved incidents become retrievable
context for future memory_search_similar lookups.

The summary text is embedded via Bedrock Titan Text v2 (1024-dim, normalized)
using the shared backend.embed helper, and stored alongside the structured
incident_jsonb and tags. Deduplication is enforced via an optional
idempotency_key: when omitted, a stable key is derived from summary + the
incident's cve_id, so repeated agent runs do not insert duplicate memories.
"""
import hashlib
import json
from typing import Any, Optional

from .db import get_psycopg_conn


def _derive_idempotency_key(summary: str, incident_jsonb: dict) -> str:
    """Stable dedup key from summary + cve_id (sha256, prefixed for readability)."""
    cve_id = ""
    if isinstance(incident_jsonb, dict):
        cve_id = str(incident_jsonb.get("cve_id", ""))
    digest = hashlib.sha256(f"{summary}\x00{cve_id}".encode("utf-8")).hexdigest()
    return f"mem-{digest[:32]}"


def _vector_literal(vec: list[float]) -> str:
    """Render a float list as a pgvector-compatible literal, e.g. '[0.1,0.2]'."""
    return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"


def memory_store(
    summary: str,
    incident_jsonb: dict,
    tags: Optional[list[str]] = None,
    idempotency_key: Optional[str] = None,
) -> dict[str, Any]:
    """
    Insert a new semantic_memory row with a real Titan embedding.

    Params
      summary: Human-readable TLDR of the incident (embedded via Titan v2).
      incident_jsonb: Structured incident data (cve_id, asset, decision,
                      outcome, etc.).
      tags: Optional key terms for filtering.
      idempotency_key: Optional stable dedup key. When omitted, derived from
                       summary + incident_jsonb.cve_id.

    Returns
      {
        success: bool,
        memory_id: str,        // the row's UUID (existing row if dedup hit)
        created: bool,         // False if an existing row matched the key
        idempotency_key: str,
      } or {success: False, error: str}.
    """
    if not summary:
        return {"success": False, "error": "summary is required."}

    # Embed the summary. Imported lazily so import-time failures (missing boto3)
    # surface as a clean tool error rather than breaking module import.
    try:
        from ..embed import embed_text
    except ImportError:
        try:
            from embed import embed_text  # type: ignore
        except ImportError as exc:
            return {"success": False, "error": f"embedding helper unavailable: {exc}"}

    key = idempotency_key or _derive_idempotency_key(summary, incident_jsonb)

    try:
        vector = embed_text(summary)
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": f"Titan embedding failed: {exc}"}

    conn = get_psycopg_conn()
    cur = conn.cursor()
    try:
        # Insert; on idempotency_key conflict, do nothing and fetch the existing row.
        cur.execute(
            """
            INSERT INTO semantic_memory
                (incident_jsonb, summary, tags, embedding, embedded_at, idempotency_key)
            VALUES (%s, %s, %s, %s::VECTOR(1024), now(), %s)
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING memory_id
            """,
            (
                json.dumps(incident_jsonb),
                summary,
                tags,
                _vector_literal(vector),
                key,
            ),
        )
        row = cur.fetchone()
        if row is not None:
            return {
                "success": True,
                "memory_id": str(row[0]),
                "created": True,
                "idempotency_key": key,
            }

        # Conflict: a row with this key already exists. Return it.
        cur.execute(
            "SELECT memory_id FROM semantic_memory WHERE idempotency_key = %s",
            (key,),
        )
        existing = cur.fetchone()
        return {
            "success": True,
            "memory_id": str(existing[0]) if existing else None,
            "created": False,
            "idempotency_key": key,
        }
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()
