-- Seed data for a polished, camera-ready critical-CVE scenario (healthcare narrative)
-- "A new critical CVE or advisory is ingested.
--  The system links it to a known production internet-facing patient-data asset.
--  The agent retrieves prior similar cases from CockroachDB long-term memory.
--  Governance evaluates whether downstream remediation can proceed automatically.
--  The system records the result and the full action trail in CockroachDB."
--
-- Run with: cockroach sql --url "$COCKROACH_URL" -f backend/db/seed.sql
--
-- This scenario is tuned for the demo video (see funding/DEMO_VIDEO_STORYBOARD.md):
--   * clean, healthcare-flavored asset name (phi-gateway-prod-01)
--   * a full audit timeline using the colored-node actions the UI renders
--     (CREATED, ASSIGNED, STATUS_CHANGED, SEMANTIC_MEMORY_QUERY, POLICY_EVALUATION)
--   * a decisions row with a written rationale so the Governance card shows a real,
--     explainable decision (manual_review) rather than only a policy-check fallback
--   * several CRITICAL + internet-facing prior incidents so the semantic-memory
--     recall card fills with high-similarity matches (KNN pre-filters on
--     severity + exposure, so matching metadata is required to surface them)
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

-- 1) Production internet-facing patient-data asset (fixed UUID; referenced below)
INSERT INTO assets (asset_id, name, description, asset_type, environment, exposure, owner_team, fqdn, tags)
VALUES (
    '4bf51d97-474c-4244-8806-7c545565915d',
    'phi-gateway-prod-01',
    'Production patient-data API gateway (handles ePHI in transit)',
    'kubernetes_workload',
    'production',
    'internet-facing',
    'platform-security',
    'api.patient-portal.example-health.com',
    '{"component":"api-gateway","tier":"tier-0","sla":"24x7","data_class":"ePHI","compliance":"HIPAA"}'
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

-- 4) Sample package (the vulnerable OpenSSL on the asset)
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
-- ePHI-handling assets require manual review before any remediation
('manual-review-ephi',
 'Assets handling ePHI require manual review to preserve HIPAA change-control',
 jsonb_build_object('data_class', 'ePHI'), 'manual_review',
 'ePHI-handling systems require documented, HIPAA-compliant change control.', true),
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
-- The KNN endpoint pre-filters candidates by the finding's own severity
-- (CRITICAL) and exposure (internet-facing), so the top matches below share
-- that metadata and will surface with high similarity in the recall card.
INSERT INTO semantic_memory (incident_jsonb, summary, tags)
VALUES
-- Closest analog: same package family, same asset, CRITICAL + internet-facing, manual_review
('{"cve_id":"CVE-2023-5678","asset_name":"phi-gateway-prod-01","exposure":"internet-facing","severity":"CRITICAL","decision":"manual_review","outcome":"patched_during_window","timestamp":"2023-11-15T14:30:00Z"}'::JSONB,
 'OpenSSL CVE-2023-5678 on phi-gateway-prod-01: governance required manual review; patched during the next approved HIPAA change window with zero downtime.',
 ARRAY['openssl', 'critical', 'internet-facing', 'manual-review', 'patching-window', 'ephi']
),
-- Same class: TLS library, CRITICAL + internet-facing, manual_review
('{"cve_id":"CVE-2024-3094","asset_name":"edge-tls-terminator","exposure":"internet-facing","severity":"CRITICAL","decision":"manual_review","outcome":"patched_during_window","timestamp":"2024-04-02T08:10:00Z"}'::JSONB,
 'xz/liblzma backdoor (CVE-2024-3094) on edge-tls-terminator: internet-facing critical; manual review confirmed no exposure to the affected build, then patched under change control.',
 ARRAY['supply-chain', 'critical', 'internet-facing', 'manual-review', 'tls']
),
-- Same posture: cert-validation flaw, CRITICAL + internet-facing, manual_review
('{"cve_id":"CVE-2022-3602","asset_name":"partner-api-ingress","exposure":"internet-facing","severity":"CRITICAL","decision":"manual_review","outcome":"mitigated","timestamp":"2022-11-01T16:45:00Z"}'::JSONB,
 'OpenSSL punycode buffer overflow (CVE-2022-3602) on partner-api-ingress: internet-facing critical; manual review, mitigated with client-cert restrictions ahead of full patch.',
 ARRAY['openssl', 'critical', 'internet-facing', 'manual-review', 'x509']
),
-- Related but HIGH severity — still internet-facing, still manual_review
('{"cve_id":"CVE-2024-1234","asset_name":"legacy-auth-proxy","exposure":"internet-facing","severity":"HIGH","decision":"manual_review","outcome":"mitigated","timestamp":"2024-03-05T09:22:00Z"}'::JSONB,
 'Legacy auth proxy CVE-2024-1234: policy ruled manual review due to internet-facing exposure; mitigated with WAF rules pending a maintenance window.',
 ARRAY['auth', 'proxy', 'high', 'internet-facing', 'manual-review', 'waf']
),
-- Contrasting outcome: internal MEDIUM auto-allowed (shows the policy discriminates)
('{"cve_id":"CVE-2023-9876","asset_name":"internal-log-bus","exposure":"internal-vpc","severity":"MEDIUM","decision":"allow","outcome":"auto-patched","timestamp":"2023-12-02T03:15:00Z"}'::JSONB,
 'Internal log-bus CVE-2023-9876: policy permitted auto-remediation; agent applied the patch in under 5 minutes with no downtime.',
 ARRAY['log-bus', 'medium', 'internal', 'allow', 'auto-patched']
);

-- 7) The finding for the scenario (would be produced by zdl_ingest; seeded for the demo)
INSERT INTO findings (finding_id, cve_id, asset_id, status, proposed_severity, approved_severity, exploitability_score, exploitability_rationale, remediation_priority, sla_due_at, owner_team, decision_state, idempotency_key)
VALUES (
    'b2c3d4e5-6f70-48a9-90b1-a2b3c4d5e6f7',
    'CVE-2024-7169',
    '4bf51d97-474c-4244-8806-7c545565915d',
    'investigating',
    'CRITICAL', 'CRITICAL',
    9.8,
    'Trivial exploit: remote, unauthenticated bypass of certificate constraints via a crafted chain; public PoC available. Asset terminates TLS for a patient-data (ePHI) API, so exploitation risks both integrity and confidentiality of regulated data.',
    'IMMEDIATE',
    now() + INTERVAL '7 days',
    'platform-security',
    'manual_review',
    'ingest-CVE-2024-7169-phi-gateway-prod-01'
);

-- 8) Governance decision row: an explainable manual_review with written rationale.
-- The /api/governance endpoint prefers a decisions row over the timeline fallback,
-- so this makes the Governance card show a real decision + rationale on camera.
INSERT INTO decisions (finding_id, proposal_jsonb, proposed_by, decision_score, decided_by, decided_at, rationale)
VALUES (
    'b2c3d4e5-6f70-48a9-90b1-a2b3c4d5e6f7',
    jsonb_build_object(
        'action_id', 'remediate-CVE-2024-7169-phi-gateway-prod-01',
        'action', 'patch_package',
        'target', 'phi-gateway-prod-01',
        'change', 'Upgrade openssl 3.0.10 -> 3.0.12 and rotate serving certificates',
        'severity', 'CRITICAL',
        'exposure', 'internet-facing',
        'data_class', 'ePHI'
    ),
    'zdl_governance',
    'manual_review',
    'zdl_governance',
    now(),
    'DECISION: manual_review. This asset is an internet-facing, tier-0 service that handles ePHI, so it matches three governance rules — manual-review-critical-internet, manual-review-tier0, and manual-review-ephi. Under HIPAA change-control, remediation of an ePHI system must be documented and executed in an approved change window; automated remediation is therefore denied. Recommended path: schedule the OpenSSL 3.0.12 upgrade and certificate rotation in the next change window, mirroring the successful CVE-2023-5678 remediation on this same asset.'
);

-- 9) Full audit timeline for the finding. Uses the exact action names the UI
-- color-codes (CREATED, ASSIGNED, STATUS_CHANGED, SEMANTIC_MEMORY_QUERY,
-- POLICY_EVALUATION) plus a policy_check event that backs the governance
-- fallback path. Timestamps are staggered so the timeline reads as a sequence.
INSERT INTO action_timeline (finding_id, actor_type, actor_id, action, target_table, target_id, payload_json, created_at)
VALUES
-- Ingest agent creates the finding from the scanner advisory
('b2c3d4e5-6f70-48a9-90b1-a2b3c4d5e6f7', 'agent', 'zdl_ingest',
 'CREATED', 'findings', 'b2c3d4e5-6f70-48a9-90b1-a2b3c4d5e6f7',
 jsonb_build_object('cve_id', 'CVE-2024-7169', 'severity', 'CRITICAL', 'source', 'scanner-automated'),
 now() - INTERVAL '9 minutes'),
-- Supervisor routes it to the owning team
('b2c3d4e5-6f70-48a9-90b1-a2b3c4d5e6f7', 'agent', 'zdl_supervisor',
 'ASSIGNED', 'findings', 'b2c3d4e5-6f70-48a9-90b1-a2b3c4d5e6f7',
 jsonb_build_object('owner_team', 'platform-security', 'remediation_priority', 'IMMEDIATE'),
 now() - INTERVAL '8 minutes'),
-- Status moves to investigating
('b2c3d4e5-6f70-48a9-90b1-a2b3c4d5e6f7', 'agent', 'zdl_supervisor',
 'STATUS_CHANGED', 'findings', 'b2c3d4e5-6f70-48a9-90b1-a2b3c4d5e6f7',
 jsonb_build_object('from', 'new', 'to', 'investigating'),
 now() - INTERVAL '7 minutes'),
-- Ingest agent queries semantic memory for prior similar incidents
('b2c3d4e5-6f70-48a9-90b1-a2b3c4d5e6f7', 'agent', 'zdl_ingest',
 'SEMANTIC_MEMORY_QUERY', 'semantic_memory', NULL,
 jsonb_build_object('top_match_cve', 'CVE-2023-5678', 'matches_returned', 3),
 now() - INTERVAL '5 minutes'),
-- Governance agent evaluates policy (colored POLICY_EVALUATION node)
('b2c3d4e5-6f70-48a9-90b1-a2b3c4d5e6f7', 'agent', 'zdl_governance',
 'POLICY_EVALUATION', 'decisions', 'b2c3d4e5-6f70-48a9-90b1-a2b3c4d5e6f7',
 jsonb_build_object('matched_rules', 'manual-review-critical-internet, manual-review-tier0, manual-review-ephi', 'decision', 'manual_review'),
 now() - INTERVAL '3 minutes'),
-- policy_check event backs the /api/governance fallback path (kept for robustness)
('b2c3d4e5-6f70-48a9-90b1-a2b3c4d5e6f7', 'agent', 'zdl_governance',
 'policy_check', 'findings', 'b2c3d4e5-6f70-48a9-90b1-a2b3c4d5e6f7',
 jsonb_build_object(
    'matched_rule_name', 'manual-review-critical-internet',
    'decision', 'manual_review',
    'timestamp', (now() - INTERVAL '3 minutes')::STRING
 ),
 now() - INTERVAL '3 minutes');

-- Executing this seed creates one complete, demo-ready scenario: an internet-facing
-- production ePHI asset with a critical CVE, prior similar incidents recalled from
-- distributed vector memory, an explainable governance decision (manual_review) with
-- written rationale, and a full, color-coded audit timeline — the artifact the 2026
-- HIPAA Security Rule requires. Demonstrates both CockroachDB features (MCP tool
-- service + distributed vector index) end-to-end.
