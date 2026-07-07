# Zero Day Librarian Backend Quickstart

This is the backend service and business logic for the Zero Day Librarian project.

## Overview

The backend provides:

- **Persistent layer**: CockroachDB Cloud tables + distributed vector index
- **Tool logic**: four gateway contract implementations (`finding_create_or_update`, `policy_evaluate_action`, `timeline_append_event`, `memory_search_similar`)
- **API Service**: FastAPI endpoints mirroring the tool contracts for local testing/development
- **Tooling**: script to refresh semantic memory vectors with Bedrock Titan embeddings

## Setup

### 1. Install dependencies

```bash
cd backend
pip install -e .             # installs psycopg, fastapi, pytest
```

### 2. Ensure CockroachDB Cloud connectivity

- Your `.env.local` (in `agentcore/`) must contain:
  ```env
  COCKROACH_URL="postgresql://<user>:<pass>@<cluster>.cockroachlabs.cloud:26257/zdl_db?sslmode=verify-full"
  ```

### 3. Schema + Seed (optional if already applied)

```bash
# If you need to re-apply:
cockroach sql --url "$COCKROACH_URL" -f backend/db/schema.sql
cockroach sql --url "$COCKROACH_URL" -f backend/db/seed.sql
```

### 4. Validate connectivity

```bash
python -c "from backend.tools.db import get_psycopg_conn; conn = get_psycopg_conn(); cur = conn.execute('SELECT count(*) FROM findings'); print('findings:', cur.fetchone()[0]); conn.close()"
```

## Running the FastAPI service

Start the local tool service:

```bash
python -m backend.main  # listens on http://127.0.0.1:8010

# Or with hot reload:
uvicorn backend.main:app --reload
```

Endpoints:

- `POST /v1/finding_create_or_update` – upsert a finding
- `POST /v1/policy_evaluate_action` – determine allow/deny/manual review
- `POST /v1/timeline_append_event` – append audit event
- `POST /v1/memory_search_similar` – find similar historical incidents by vector search

## Running tests

Tests run against the **live CockroachDB Cloud** database.

```bash
# At repo root, with COCKROACH_URL set:
export $(grep '^COCKROACH_URL=' agentcore/.env.local | sed 's/"//g')
pytest                            # or pytest backend/tests -v

# Run a single tool subset:
pytest backend/tests/test_tools.py::test_memory_vector_knn
```

## Optional: Update with real Titan embeddings

The seeded `semantic_memory` embeds placeholder vectors generated in SQL.
To replace them with Bedrock Titan Text v2 embeddings:

```bash
export $(grep '^COCKROACH_URL=' agentcore/.env.local | sed 's/"//g')
python backend/embed_titan.py   # fetches embeddings via boto3 bedrock-runtime
```

This will read `semantic_memory.summary` columns, call `invoke_model`, and
update the `embedding` column with the 1024-dim embedding.

## Notes

- The backend **tools directory** contains the reusable logic used both by
  the local FastAPI service and by the AWS Lambda MCP handler (`zdl-tools-handler`).
  Keep contracts identical so local tests predict cloud behavior.

- For security, `backend/tools/db.py` handles the CockroachDB connection
  CA certificate path automatically. For previsioned situations, you can set
  `COCKROACH_SSLROOTCERT` to override the bundled cert path.
