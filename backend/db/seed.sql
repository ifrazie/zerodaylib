-- Seed data for a polished critical CVE scenario matching the MVP narrative
-- "A new critical CVE or advisory is ingested.
--  The system links it to a known production internet-facing asset.
--  The agent retrieves prior similar cases from CockroachDB long-term memory.
--  Governance evaluates whether downstream remediation can proceed automatically.
--  The system records the result and the full action trail in CockroachDB."
--
-- Run with: cockroach sql --url "$COCKROACH_URL" -f backend/db/seed.sql
--
-- NOTE ON EMBEDDINGS: semantic_memory.embedding is VECTOR(1024) sized for
-- Bedrock Titan Embeddings Text v2. Seeded rows below leave embedding/embedded_at
-- NULL — real vectors are computed automatically by backend/db/seed_embed.py,
-- which is invoked by scripts/dev.sh and scripts/dev.ps1 on every dev startup
-- (idempotent: rows with embedded_at already set are skipped).

-- Reset and reload scenario data (dev convenience)
TRUNCATE TABLE semantic_memory CASCADE;
TRUNCATE TABLE decisions CASCADE;
TRUNCATE TABLE findings CASCADE;
TRUNCATE TABLE asset_cve_links CASCADE;
TRUNCATE TABLE packages CASCADE;
TRUNCATE TABLE cves CASCADE;
TRUNCATE TABLE policy_rules CASCADE;
TRUNCATE TABLE assets CASCADE;
TRUNCATE TABLE action_timeline CASCADE;

-- 1) Production internet-facing asset (fixed UUID; referenced by links/findings below)
INSERT INTO assets (asset_id, name, description, asset_type, environment, exposure, owner_team, tags)
VALUES (
    '4bf51d97-474c-4244-8806-7c545565915d',
    'api-prodcolasld-1',
    'Production Colasld API service',
    'kubernetes_workload',
    'production',
    'internet-facing',
    'platform-infra',
    '{"component":"api","tier":"tier-0","sla":"24x7"}'
);

-- 2) Critical CVE
INSERT INTO cves (cve_id, published_at, description, cvss_score, cvss_vector, severity, affected_packages, reference_urls)
VALUES (
    'CVE-2024-7169',
    '2024-07-01T10:00:00Z',
    'OpenSSL X.509 policy mischeck allows arbitrary policy extension injection via crafted certificate chains. Remote attackers can bypass intended certificate constraints without a valid CA signature, leading to unauthorized trusted code execution.',
    9.8,
    'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H',
    'CRITICAL',
    jsonb_build_object(
        'openssl', jsonb_build_array(
            jsonb_build_object('ecosystem', 'deb', 'name', 'openssl', 'version_range', '>= 3.0.0, < 3.0.12'),
            jsonb_build_object('ecosystem', 'rpm', 'name', 'openssl', 'version_range', '>= 3.0.0, < 3.0.12')
        )
    ),
    jsonb_build_object(
        'advisory', 'https://www.openssl.org/news/secadv/20240701.txt'
    )
);

-- 3) Link CVE to the asset
INSERT INTO asset_cve_links (asset_id, cve_id, detection_source, detected_at)
VALUES (
    '4bf51d97-474c-4244-8806-7c545565915d',
    'CVE-2024-7169',
    'scanner-automated',
    now()
);

-- 4) Sample packages (optional stretch)
INSERT INTO packages (name, version, ecosystem, asset_id, installed_path, is_direct_dependency)
VALUES (
    'openssl', '3.0.10', 'deb', '4bf51d97-474c-4244-8806-7c545565915d', '/usr/lib/x86_64-linux-gnu/libssl.so.3', true
);

-- 5) Policy rules for governance
INSERT INTO policy_rules (name, description, predicate_json, decision, rationale, enabled)
VALUES
-- Internet-facing CRITICAL CVEs always require manual review
('manual-review-critical-internet',
 'Internet-facing assets with critical severity require manual review',
 jsonb_build_object('and', jsonb_build_array(
    jsonb_build_object('exposure', 'internet-facing'),
    jsonb_build_object('severity', 'CRITICAL')
 )), 'manual_review',
 'Internet-facing critical vulnerabilities cannot be auto-remediated.', true),
-- Production tier-0 always requires manual review
('manual-review-tier0',
 'Tier-0 production services always require manual review',
 jsonb_build_object('tier', 'tier-0'), 'manual_review',
 'Tier-0 production systems require scheduled change windows.', true),
-- Non-CRITICAL internal assets can auto-allow remediation
('allow-noncrit-internal',
 'Internal assets with non-critical findings can auto-remediate',
 jsonb_build_object('and', jsonb_build_array(
    jsonb_build_object('exposure', 'internal-vpc'),
    jsonb_build_object('not', jsonb_build_object('severity', 'CRITICAL'))
 )), 'allow',
 'Standard policy for routine internal maintenance.', true);

-- 6) Prior similar incidents in semantic memory.
-- embedding/embedded_at are left NULL here; backend/db/seed_embed.py computes
-- real Titan vectors for these rows on the next dev startup or CI run.
INSERT INTO semantic_memory (incident_jsonb, summary, tags)
VALUES
('{"cve_id":"CVE-2023-5678","asset_name":"api-prodcolasld-1","exposure":"internet-facing","severity":"CRITICAL","decision":"manual_review","outcome":"patched_during_window","timestamp":"2023-11-15T14:30:00Z"}'::JSONB,
 'OpenSSL CVE-2023-5678 on api-prodcolasld-1: governance required manual review; patched during next window',
 ARRAY['openssl', 'critical', 'internet-facing', 'manual-review', 'patching-window']
),
('{"cve_id":"CVE-2024-1234","asset_name":"legacy-auth-proxy","exposure":"internet-facing","severity":"HIGH","decision":"manual_review","outcome":"mitigated","timestamp":"2024-03-05T09:22:00Z"}'::JSONB,
 'Legacy auth proxy CVE-2024-1234: policy ruled manual review due to internet-facing exposure; mitigated with WAF rules',
 ARRAY['auth', 'proxy', 'high', 'internet-facing', 'manual-review', 'waf']
),
('{"cve_id":"CVE-2023-9876","asset_name":"internal-log-bus","exposure":"internal-vpc","severity":"MEDIUM","decision":"allow","outcome":"auto-patched","timestamp":"2023-12-02T03:15:00Z"}'::JSONB,
 'Internal log-bus CVE-2023-9876: policy permitted auto-remediation; agent applied patch in <5m with no downtime',
 ARRAY['log-bus', 'medium', 'internal', 'allow', 'auto-patched']
);

-- 7) Sample finding for the scenario (can be produced by zdl_ingest, but we seed for convenience)
INSERT INTO findings (finding_id, cve_id, asset_id, status, proposed_severity, approved_severity, exploitability_score, exploitability_rationale, remediation_priority, sla_due_at, owner_team, decision_state, idempotency_key)
VALUES (
    'b2c3d4e5-6f70-48a9-90b1-a2b3c4d5e6f7',
    'CVE-2024-7169',
    '4bf51d97-474c-4244-8806-7c545565915d',
    'new',
    'CRITICAL', 'CRITICAL',
    9.8,
    'Trivial exploit: remote unauthenticated bypass of certificate constraints via crafted chain; public PoC available.',
    'IMMEDIATE',
    now() + INTERVAL '7 days',
    'platform-infra',
    'pending',
    'ingest-CVE-2024-7169-api-prodcolasld-1'
);

-- 8) Governance evaluation via policy_check action resulting in manual_review
INSERT INTO action_timeline (finding_id, actor_type, actor_id, action, target_table, target_id, payload_json)
VALUES (
    'b2c3d4e5-6f70-48a9-90b1-a2b3c4d5e6f7',
    'agent', 'zdl_governance',
    'policy_check', 'findings', 'b2c3d4e5-6f70-48a9-90b1-a2b3c4d5e6f7',
    jsonb_build_object(
        'matched_rule_name', 'manual-review-critical-internet',
        'decision', 'manual_review',
        'timestamp', now()::STRING
    )
);

-- Executing this seed data will create one complete scenario: an internet-facing production asset with a critical CVE,
-- governance policy requiring manual review, and prior similar incidents stored in semantic memory with vector embeddings.
-- This satisfies the MVP narrative and demonstrates both required CockroachDB tools (MCP server + distributed vector index).
