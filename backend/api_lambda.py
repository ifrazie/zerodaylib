"""
backend/api_lambda.py — AWS Lambda entrypoint for the ZDL frontend read API.

This wraps the existing FastAPI application (backend/main.py) with Mangum so the
same HTTP contracts served locally by uvicorn (the `/api/*` read endpoints and
the `/v1/*` tool endpoints) run unchanged behind API Gateway (HTTP API).

Contrast with backend/lambda_handler.py, which is the AgentCore *Gateway* MCP
target and only dispatches the `/v1` tool functions (no HTTP layer). This module
is the HTTP API surface consumed by the CloudFront `/api/*` behavior.

Environment variables (read by backend/tools/db.py and backend/lambda_handler-style resolution):
  COCKROACH_URL          — psycopg connection string (prefer Secrets Manager)
  COCKROACH_SECRET_ARN   — Secrets Manager ARN for COCKROACH_URL (preferred over env)
  COCKROACH_SSLROOTCERT  — optional; defaults to the bundled CA cert
  FRONTEND_ORIGIN        — CloudFront origin allowed by CORS (see main.py)
  AWS_REGION / AWS_DEFAULT_REGION — resolved automatically in the Lambda runtime

Handler reference (for the Lambda config): backend/api_lambda.handler
"""

from __future__ import annotations

import json
import logging
import os
import sys

# ── Make backend/ importable whether invoked as a Lambda package
# (cwd is /var/task) or as part of the monorepo (cwd is repo root). ────────────
_this_dir = os.path.dirname(os.path.abspath(__file__))
for _candidate in (_this_dir, os.path.dirname(_this_dir)):
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

logger = logging.getLogger("zdl-api")
logger.setLevel(logging.INFO)


def _resolve_cockroach_url() -> None:
    """Resolve COCKROACH_URL from Secrets Manager once per container lifetime.

    If COCKROACH_URL is already set, do nothing. Otherwise, if COCKROACH_SECRET_ARN
    is set, fetch the secret and write it into the environment so backend/tools/db.py
    picks it up transparently — identical behavior to lambda_handler.py.
    """
    if os.environ.get("COCKROACH_URL"):
        return

    secret_arn = os.environ.get("COCKROACH_SECRET_ARN")
    if not secret_arn:
        logger.warning(
            "Neither COCKROACH_URL nor COCKROACH_SECRET_ARN is set; "
            "DB calls will fall back to local defaults."
        )
        return

    try:
        import boto3

        region = os.environ.get(
            "AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        )
        sm = boto3.client("secretsmanager", region_name=region)
        value = sm.get_secret_value(SecretId=secret_arn)
        url = value.get("SecretString") or ""
        if url and url.strip().startswith("{"):
            # If stored as a JSON object with a 'url' key, unwrap it.
            try:
                url = json.loads(url).get("url", "") or ""
            except (json.JSONDecodeError, AttributeError):
                pass
        if url:
            os.environ["COCKROACH_URL"] = url
            logger.info("COCKROACH_URL resolved from Secrets Manager.")
        else:
            logger.error("COCKROACH_SECRET_ARN secret value was empty.")
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to resolve COCKROACH_URL from Secrets Manager: %s", exc)


# Resolve DB credentials before importing the app so any module-level DB setup
# in main.py / tools sees a populated COCKROACH_URL.
_resolve_cockroach_url()

from mangum import Mangum  # noqa: E402
from main import app  # noqa: E402

# API Gateway HTTP API (payload v2.0) and REST API (v1.0) are both auto-detected
# by Mangum. api_gateway_base_path is left at "/" because the CloudFront `/api/*`
# behavior forwards the full path (including `/api`) to the origin unchanged.
handler = Mangum(app, lifespan="off")
