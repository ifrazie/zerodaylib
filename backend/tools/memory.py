"""
Tool: memory_search_similar

Search semantic_memory for prior incidents similar to the current context.
This tool uses CockroachDB's distributed vector index (idx_memory_embedding)
to perform efficient nearest-neighbor search over 1024-dimensional Titan Text
v2 embeddings.

Intended for agents retrieving historical context and learning from prior
decisions or governance outcomes. By retrieving relevant prior cases,
agents can apply pattern recognition and avoid repeating the same mistakes.
Uses L2 distance over the VECTOR(1024) column; most similar matches have
the smallest distances.
"""
import psycopg
from typing import Any, Optional

from .db import get_psycopg_conn


def memory_search_similar(
    query_vector: list[float],
    limit: int = 3,
    filters: Optional[dict] = None,
) -> dict[str, Any]:
    """
    Search for K nearest neighbors in semantic_memory.

    Params
      query_vector: A 1024-dim float list (Bedrock Titan Text v2 embedding).
      limit: Max results (1-10), default 3.
      filters: Optionalflat k/v constraints on incident fields (e.g., 
               {"cve_id":"CVE-2024-1234"}). Only rows matching these are candidates.

    Returns
      {
        matches: list[{memory_id, incident_jsonb, summary, tags, distance}],
        limit: int,
        total_unfiltered: int (count of rows matching filters before vector-ordering)
      }
    """
    if limit < 1 or limit > 10:
        limit = 3

    conn = get_psycopg_conn()
    cur = conn.cursor()

    try:
        qvec_expr = f"('[' || array_to_string(ARRAY{list(query_vector)}, ',') || ']')::VECTOR(1024)"

        where_clauses = []
        filter_args = []
        if filters:
            for k, v in filters.items():
                where_clauses.append(f"incident_jsonb->>'{k}' = %s")
                filter_args.append(str(v))

        where = "" if not where_clauses else "WHERE " + " AND ".join(where_clauses)

        # Total rows matching filters before vector ordering
        count_sql = f"SELECT count(*) FROM semantic_memory {where}"
        cur.execute(count_sql, filter_args)
        total_unfiltered = cur.fetchone()[0]

        # Nearest-N by L2 distance
        knn_sql = (
            f"SELECT memory_id, incident_jsonb, summary, tags, embedding <-> {qvec_expr} AS distance"
            f" FROM semantic_memory {where}\
"
            " ORDER BY distance\n"
            " LIMIT %s"
        )
        cur.execute(knn_sql, (*filter_args, limit))
        rows = cur.fetchall()

        matches = []
        for mid, incident_jsonb, summary, tags, dist in rows:
            matches.append({
                "memory_id": str(mid),
                "incident_jsonb": incident_jsonb,
                "summary": summary,
                "tags": tags,
                "distance": float(dist),
            })

        return {
            "matches": matches,
            "limit": limit,
            "total_unfiltered": total_unfiltered,
            "success": True,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()
