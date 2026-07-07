# Phase 5 Deploy Runbook — ZeroDayLib Cloud Integration

Connect the locally-tested `backend/tools/*` logic to the live Bedrock AgentCore
flow so that agents (`zdl_supervisor`, `zdl_ingest`, `zdl_governance`) invoke real
CockroachDB tool calls through the existing MCP gateway.

## Architecture recap

```
AgentCore Runtime (Strands agent)
  └─► MCP Gateway zdl-gateway-frkgbxbipc  (existing, out-of-band, AWS_IAM auth)
        └─► Lambda zdl-tools-handler       (new — this runbook deploys it)
              └─► CockroachDB Cloud zdl_db  (existing, verify-full TLS)
```

## Prerequisites

```bash
# AWS CLI v2.x with bedrock-agentcore-control support (CLI ≥ 2.22 recommended)
aws --version                   # must show 2.x
aws sts get-caller-identity     # must show account 606713070136

# Python 3.10+ and pip (for layer build + backend.db.seed_embed)
python3 --version

# Docker (for the psycopg ARM64 layer build)
docker --version

# jq (used in validation commands)
jq --version
```

Set a shell variable for convenience throughout this runbook:

```bash
export ACCOUNT_ID=606713070136
export REGION=us-east-1
export GATEWAY_ID=zdl-gateway-frkgbxbipc
export FN_NAME=zdl-tools-handler
export ROLE_NAME=zdl-tools-handler-role
export SECRET_NAME=zerodaylib/cockroach-url
```

---

## Step 1 — Build the deployment artifacts

From the **repo root**:

```bash
# Build the handler zip (fast, no Docker needed)
bash backend/package_lambda.sh --zip

# Build the psycopg layer (requires Docker — ARM64 manylinux build)
bash backend/package_lambda.sh --layer

# Or build both at once:
bash backend/package_lambda.sh
```

Verify both artifacts exist:

```bash
ls -lh dist/zdl-tools-handler.zip dist/zdl-tools-layer.zip
# Expected: handler ~16 KB, layer ~5-10 MB
```

**Windows (no WSL):** For the handler zip only, run `./backend/package_lambda.ps1` in
PowerShell. For the layer, use WSL: `wsl bash backend/package_lambda.sh --layer`.

---

## Step 2 — Store COCKROACH_URL in Secrets Manager

Store the CockroachDB connection string as a plain-string secret. The Lambda
reads it via `COCKROACH_SECRET_ARN` at cold-start.

```bash
# Retrieve the URL from .env.local (strip quotes)
COCKROACH_URL=$(grep '^COCKROACH_URL=' agentcore/.env.local | sed 's/COCKROACH_URL=//;s/"//g')

aws secretsmanager create-secret \
  --name "$SECRET_NAME" \
  --description "CockroachDB Cloud connection string for zdl-tools-handler Lambda" \
  --secret-string "$COCKROACH_URL" \
  --region "$REGION"

# Note the ARN — you will need it in Step 5
SECRET_ARN=$(aws secretsmanager describe-secret \
  --secret-id "$SECRET_NAME" \
  --region "$REGION" \
  --query 'ARN' --output text)
echo "Secret ARN: $SECRET_ARN"
```

If the secret already exists, update it:

```bash
aws secretsmanager update-secret \
  --secret-id "$SECRET_NAME" \
  --secret-string "$COCKROACH_URL" \
  --region "$REGION"
```

---

## Step 3 — Create the IAM execution role

```bash
# Trust policy (Lambda can assume the role)
aws iam create-role \
  --role-name "$ROLE_NAME" \
  --assume-role-policy-document file://backend/iam/zdl-tools-handler-trust.json

# Inline permissions (Secrets Manager, Bedrock Titan, CloudWatch Logs)
aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name zdl-tools-handler-policy \
  --policy-document file://backend/iam/zdl-tools-handler-policy.json

# Capture the role ARN
ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
echo "Role ARN: $ROLE_ARN"
```

Wait ~15 seconds for IAM propagation before continuing.

---

## Step 4 — Publish the psycopg Lambda layer

```bash
LAYER_VERSION_ARN=$(aws lambda publish-layer-version \
  --layer-name zdl-psycopg-arm64 \
  --description "psycopg[binary] ARM64 + CockroachDB CA cert for zdl-tools-handler" \
  --zip-file fileb://dist/zdl-tools-layer.zip \
  --compatible-runtimes python3.12 \
  --compatible-architectures arm64 \
  --region "$REGION" \
  --query 'LayerVersionArn' --output text)
echo "Layer ARN: $LAYER_VERSION_ARN"
```

---

## Step 5 — Deploy the Lambda function

```bash
aws lambda create-function \
  --function-name "$FN_NAME" \
  --runtime python3.12 \
  --architectures arm64 \
  --role "$ROLE_ARN" \
  --handler lambda_handler.handler \
  --zip-file fileb://dist/zdl-tools-handler.zip \
  --layers "$LAYER_VERSION_ARN" \
  --timeout 60 \
  --memory-size 512 \
  --description "ZeroDayLib MCP tool contracts — finding, policy, timeline, memory search" \
  --environment "Variables={
    COCKROACH_SECRET_ARN=$SECRET_ARN,
    COCKROACH_SSLROOTCERT=/etc/zdl/cc-ca.crt,
    AWS_REGION_OVERRIDE=$REGION
  }" \
  --region "$REGION"

# Capture the Lambda ARN
LAMBDA_ARN=$(aws lambda get-function \
  --function-name "$FN_NAME" \
  --region "$REGION" \
  --query 'Configuration.FunctionArn' --output text)
echo "Lambda ARN: $LAMBDA_ARN"
```

To **update** an existing function after rebuilding the zip:

```bash
aws lambda update-function-code \
  --function-name "$FN_NAME" \
  --zip-file fileb://dist/zdl-tools-handler.zip \
  --architectures arm64 \
  --region "$REGION"
```

---

## Step 6 — Add the Lambda's egress IP to CockroachDB Cloud allowlist

Lambda uses a VPC NAT gateway or the account-level egress IP for public internet
traffic. The IP must be added to the CockroachDB Cloud cluster's IP allowlist so
the Lambda can reach `fair-dolphin-28426.j77.aws-us-east-1.cockroachlabs.cloud`.

### 6a — Find the Lambda's egress IP

Invoke the Lambda with a test event that returns the egress IP:

```bash
aws lambda invoke \
  --function-name "$FN_NAME" \
  --payload '{"action":"__ip_probe","fact_set":{}}' \
  --cli-binary-format raw-in-base64-out \
  --region "$REGION" \
  /tmp/ip-probe-response.json && cat /tmp/ip-probe-response.json
```

The response will be `{"success": false, "error": "..."}` (policy_evaluate_action
will fail to reach the DB) — that is expected. Alternatively, use a simple echo
Lambda or check the VPC/NAT configuration for a static elastic IP.

For a Lambda in the default (non-VPC) configuration, the egress IP varies per
invocation. **Recommended:** assign a static Elastic IP via VPC NAT Gateway, or
use a `/32` range. For the hackathon demo, a broad CIDR from your account's
IP allocation is acceptable.

To find the current IP without VPC:

```bash
aws lambda invoke \
  --function-name "$FN_NAME" \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  --region "$REGION" \
  /tmp/dummy.json

# Check CloudWatch Logs for the Lambda's source IP (visible in CRDB audit log)
aws logs get-log-events \
  --log-group-name /aws/lambda/$FN_NAME \
  --log-stream-name "$(aws logs describe-log-streams \
    --log-group-name /aws/lambda/$FN_NAME \
    --order-by LastEventTime --descending \
    --max-items 1 --region $REGION \
    --query 'logStreams[0].logStreamName' --output text)" \
  --region "$REGION" | jq '.events[].message' | head -20
```

### 6b — Add to CockroachDB Cloud allowlist

1. Open the [CockroachDB Cloud Console](https://cockroachlabs.cloud/).
2. Select cluster **fair-dolphin**.
3. Navigate to **Networking → IP Allowlist**.
4. Click **Add Network** → enter the Lambda egress IP/CIDR.
5. Description: `zdl-tools-handler Lambda (us-east-1)`.

For a static NAT IP this is a `/32` entry. For a dynamic Lambda (no VPC) you
may need a broader CIDR — accept the tradeoff for the demo.

---

## Step 7 — Register the Lambda as a gateway target

This attaches the Lambda to the existing `zdl-gateway-frkgbxbipc` so the agents'
MCP tool calls are routed to it. The `inlinePayload` carries the 4 tool schemas.

```bash
aws bedrock-agentcore-control update-gateway-target \
  --gateway-identifier "$GATEWAY_ID" \
  --name "zdl-tools-handler" \
  --description "ZeroDayLib tool contracts: finding, policy, timeline, memory KNN search" \
  --target-configuration '{
    "mcp": {
      "lambda": {
        "lambdaArn": "'"$LAMBDA_ARN"'",
        "toolSchema": {
          "inlinePayload": [
            {
              "name": "finding_create_or_update",
              "description": "Idempotent upsert of a vulnerability finding in CockroachDB. Re-submitting the same idempotency_key updates only non-null fields. Use during CVE ingestion and workflow state transitions.",
              "inputSchema": {
                "type": "object",
                "properties": {
                  "idempotency_key": {"type": "string", "description": "Stable unique key, e.g. ingest-CVE-2024-7169-api-prod-1. Must not change across retries."},
                  "cve_id": {"type": "string", "description": "CVE identifier e.g. CVE-2024-7169."},
                  "asset_id": {"type": "string", "description": "UUID of the affected asset."},
                  "status": {"type": "string", "description": "Lifecycle status: new, investigating, triaged, resolved, false_positive."},
                  "proposed_severity": {"type": "string", "description": "Severity before governance approval: CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL."},
                  "approved_severity": {"type": "string", "description": "Severity confirmed by governance: CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL."},
                  "exploitability_score": {"type": "number", "description": "CVSS exploitability score 0.0-10.0."},
                  "exploitability_rationale": {"type": "string", "description": "One-paragraph rationale for the exploitability assessment."},
                  "remediation_priority": {"type": "string", "description": "Urgency tier: IMMEDIATE, HIGH, NORMAL, LOW, DEFERRED."},
                  "sla_due_at": {"type": "string", "description": "ISO 8601 datetime for remediation deadline."},
                  "owner_team": {"type": "string", "description": "Team responsible for remediation."},
                  "decision_state": {"type": "string", "description": "Governance decision: pending, allow, deny, manual_review."}
                },
                "required": ["idempotency_key"]
              }
            },
            {
              "name": "policy_evaluate_action",
              "description": "Evaluate a proposed action against deterministic policy rules. Returns allow, deny, or manual_review. Most-restrictive rule wins. Call this before mutating operational state on production or internet-facing assets.",
              "inputSchema": {
                "type": "object",
                "properties": {
                  "action": {"type": "string", "description": "Action name e.g. approve_remediation, close_finding, escalate_to_soc."},
                  "fact_set": {"type": "object", "description": "Flat key-value facts for policy matching. Common keys: exposure, severity, tier, environment.", "properties": {}, "required": []}
                },
                "required": ["action", "fact_set"]
              }
            },
            {
              "name": "timeline_append_event",
              "description": "Append an immutable audit event to action_timeline. Append-only — rows are never updated or deleted. Record every agent action, governance decision, and state transition.",
              "inputSchema": {
                "type": "object",
                "properties": {
                  "actor_type": {"type": "string", "description": "Category of actor: agent, human, or system."},
                  "actor_id": {"type": "string", "description": "Specific actor identifier e.g. zdl_governance, alice."},
                  "action": {"type": "string", "description": "Action label e.g. policy_check, finding_created, decision_approved."},
                  "finding_id": {"type": "string", "description": "UUID of the related finding. Omit if not scoped to a single finding."},
                  "target_table": {"type": "string", "description": "Database table acted on e.g. findings, decisions."},
                  "target_id": {"type": "string", "description": "Row identifier (typically a UUID)."},
                  "payload_json": {"type": "object", "description": "Event-specific detail. For policy_check include matched_rule_name and decision.", "properties": {}, "required": []}
                },
                "required": ["actor_type", "actor_id", "action"]
              }
            },
            {
              "name": "memory_search_similar",
              "description": "Search semantic_memory using CockroachDB distributed vector index (KNN over VECTOR(1024) Titan embeddings). Provide query_text (embedded on-the-fly via Titan Text v2) or query_vector. Returns matches ranked by L2 distance. Use before governance decisions to surface historical outcomes.",
              "inputSchema": {
                "type": "object",
                "properties": {
                  "query_text": {"type": "string", "description": "Natural-language incident description. Embedded via Titan Text v2. Provide this or query_vector."},
                  "query_vector": {"type": "array", "description": "Pre-computed 1024-dim float embedding. Provide this or query_text.", "items": {"type": "number"}},
                  "limit": {"type": "integer", "description": "Max results 1-10. Default 3."},
                  "filters": {"type": "object", "description": "JSONB field filters applied before vector ranking. Keys are incident_jsonb field names.", "properties": {}, "required": []}
                }
              }
            }
          ]
        }
      }
    }
  }' \
  --region "$REGION"
```

Capture the target ID for reference:

```bash
TARGET_ID=$(aws bedrock-agentcore-control list-gateway-targets \
  --gateway-identifier "$GATEWAY_ID" \
  --region "$REGION" \
  --query 'items[?name==`zdl-tools-handler`].targetId' \
  --output text)
echo "Gateway target ID: $TARGET_ID"
```

Grant the gateway permission to invoke the Lambda:

```bash
aws lambda add-permission \
  --function-name "$FN_NAME" \
  --statement-id AllowAgentCoreGateway \
  --action lambda:InvokeFunction \
  --principal bedrock-agentcore.amazonaws.com \
  --source-arn "arn:aws:bedrock-agentcore:$REGION:$ACCOUNT_ID:gateway/$GATEWAY_ID" \
  --region "$REGION"
```

---

## Step 8 — Refresh semantic_memory with real Titan embeddings

Replace any placeholder or unembedded rows in `semantic_memory` with real
1024-dim Titan v2 embeddings so vector KNN returns semantically meaningful
results. This step is **idempotent**: it only embeds rows where
`embedded_at IS NULL`, so it is safe to run repeatedly (and is run
automatically by `scripts/dev.sh` / `scripts/dev.ps1` for local dev).

```bash
# Ensure AWS credentials are set for Bedrock Titan access
export COCKROACH_URL=$(grep '^COCKROACH_URL=' agentcore/.env.local | sed 's/COCKROACH_URL=//;s/"//g')
python -m backend.db.seed_embed
# Expected output: "Embedded N semantic_memory row(s) with real Titan vectors."
# Re-running with nothing to embed prints: "No unembedded semantic_memory rows found; nothing to do."
```

Verify the vectors changed and `embedded_at` is stamped:

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
import os; os.environ['COCKROACH_URL'] = open('agentcore/.env.local').read().split('COCKROACH_URL=')[1].split('\n')[0].strip('\"')
from backend.tools.db import get_psycopg_conn
conn = get_psycopg_conn()
rows = conn.execute('SELECT memory_id, embedded_at, LEFT(embedding::STRING, 60) FROM semantic_memory').fetchall()
for r in rows: print(r)
conn.close()
"
```

**Note:** If `semantic_memory` was created before the `embedded_at` column
was introduced, `backend/db/schema.sql` includes an idempotent
`ALTER TABLE semantic_memory ADD COLUMN IF NOT EXISTS embedded_at TIMESTAMPTZ;`
migration. Re-run `backend/db/schema.sql` against the cluster first if you
see an "column embedded_at does not exist" error.

---

## Step 9 — Validate end-to-end

### 9a — Smoke-test the Lambda directly

```bash
# Test policy_evaluate_action
aws lambda invoke \
  --function-name "$FN_NAME" \
  --payload '{"action":"approve_remediation","fact_set":{"exposure":"internet-facing","severity":"CRITICAL"}}' \
  --cli-binary-format raw-in-base64-out \
  --region "$REGION" \
  /tmp/policy-test.json \
  --log-type Tail \
  --query 'LogResult' \
  --output text | base64 -d | tail -5

cat /tmp/policy-test.json | jq .
# Expected: {"decision":"manual_review","matched_rule_name":"manual-review-critical-internet",...}

# Test memory_search_similar with query_text (uses Titan on-the-fly)
aws lambda invoke \
  --function-name "$FN_NAME" \
  --payload '{"query_text":"critical OpenSSL CVE on internet-facing production kubernetes","limit":2}' \
  --cli-binary-format raw-in-base64-out \
  --region "$REGION" \
  /tmp/memory-test.json
cat /tmp/memory-test.json | jq '{success,total_unfiltered,match_count: (.matches|length)}'
```

### 9b — Invoke an agent through the gateway

```bash
# Requires agentcore CLI and agent runtimes to be deployed
# (run agentcore deploy first if runtimes haven't been deployed yet — see note below)
agentcore invoke zdl_governanceAgent \
  --payload '{"prompt":"Evaluate CVE-2024-7169 on api-prodcolasld-1 (internet-facing, CRITICAL). Should remediation proceed?"}' \
  --region "$REGION"
```

### 9c — Verify a new timeline event was written

```bash
python3 -c "
import sys, os; sys.path.insert(0, 'backend')
os.environ['COCKROACH_URL'] = open('agentcore/.env.local').read().split('COCKROACH_URL=')[1].split('\n')[0].strip('\"')
from tools.db import get_psycopg_conn
conn = get_psycopg_conn()
rows = conn.execute('''
  SELECT actor_id, action, payload_json, created_at
  FROM action_timeline
  ORDER BY created_at DESC LIMIT 5
''').fetchall()
for r in rows: print(r)
conn.close()
"
```

You should see rows written by `zdl_governance` or `zdl_ingest` via the Lambda,
proving the full end-to-end path is live.

---

## Note: Deploying the agent runtimes

This runbook deploys only the Lambda tool handler. The 3 AgentCore runtimes
(`zdl_supervisorAgent`, `zdl_ingestAgent`, `zdl_governanceAgent`) are declared in
`agentcore/agentcore.json` but have not been deployed by CDK yet
(`deployed-state.json` is empty). Before Step 9b:

1. Add a deployment target to `agentcore/aws-targets.json`:
   ```json
   [{ "name": "prod", "account": "606713070136", "region": "us-east-1" }]
   ```

2. Run `agentcore validate` to confirm the schema is clean.

3. Run `agentcore deploy` to provision the 3 runtimes via CDK.

4. After deploy, `agentcore/.env.local` will be updated with the new runtime
   endpoint URLs.

The memories and gateway are consumed as external connections (by ARN) — CDK does
not touch or recreate them.

---

## Rollback

To remove the Lambda tool target from the gateway:

```bash
aws bedrock-agentcore-control delete-gateway-target \
  --gateway-identifier "$GATEWAY_ID" \
  --target-id "$TARGET_ID" \
  --region "$REGION"
```

To delete the Lambda:

```bash
aws lambda delete-function --function-name "$FN_NAME" --region "$REGION"
```

To delete the IAM role:

```bash
aws iam delete-role-policy --role-name "$ROLE_NAME" --policy-name zdl-tools-handler-policy
aws iam delete-role --role-name "$ROLE_NAME"
```
