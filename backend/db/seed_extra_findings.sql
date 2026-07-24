-- Additive seed: extra findings to fill out the dashboard table for brand-book
-- screenshots and demos. This file is ADDITIVE and idempotent — it does NOT
-- truncate anything and can be re-run safely (all inserts use ON CONFLICT ...
-- DO NOTHING / stable idempotency keys). The camera-ready CVE-2024-7169
-- scenario in seed.sql is left completely intact.
--
-- Run with: cockroach sql --url "$COCKROACH_URL" -f backend/db/seed_extra_findings.sql
--
-- Goal: a realistic spread of severities (CRITICAL/HIGH/MEDIUM/LOW), statuses
-- (new/investigating/resolved), and governance decisions
-- (manual_review/allow/deny) across a mix of internet-facing and internal
-- assets, so the Findings Dashboard table reads as a populated queue.
--
-- Each extra finding is backfilled with a full drill-in story so the detail
-- page flow (finding -> semantic memory -> governance -> audit) is coherent for
-- every row, not just the camera-ready hero in seed.sql:
--   * a decisions row whose decision_score matches the finding's decision_state
--     (so the dashboard governance badge agrees with the detail Governance card;
--      decision_score is CHECK-constrained to allow/deny/manual_review)
--   * a staggered action_timeline using the UI-colored actions
--   * posture-matching semantic_memory incidents so the recall card fills
--     (KNN pre-filters on severity + exposure)

-- 1) Extra assets (fixed UUIDs so links + findings resolve; ON CONFLICT no-op) ---
INSERT INTO assets (asset_id, name, description, asset_type, environment, exposure, owner_team, fqdn, tags)
VALUES
  ('a1000000-0000-4000-8000-000000000001', 'edge-tls-terminator', 'Public edge TLS terminator / reverse proxy', 'load_balancer', 'production', 'internet-facing', 'platform-security', 'edge.example-health.com', '{"tier":"tier-0","data_class":"none"}'),
  ('a1000000-0000-4000-8000-000000000002', 'partner-api-ingress', 'Partner-facing API ingress gateway', 'kubernetes_workload', 'production', 'internet-facing', 'integrations', 'partners.example-health.com', '{"tier":"tier-1"}'),
  ('a1000000-0000-4000-8000-000000000003', 'internal-log-bus', 'Internal log aggregation bus', 'kubernetes_workload', 'production', 'internal-vpc', 'observability', NULL, '{"tier":"tier-2"}'),
  ('a1000000-0000-4000-8000-000000000004', 'billing-worker-fleet', 'Async billing worker fleet', 'kubernetes_workload', 'production', 'internal-vpc', 'payments', NULL, '{"tier":"tier-1"}'),
  ('a1000000-0000-4000-8000-000000000005', 'dev-sandbox-api', 'Developer sandbox API server', 'server', 'development', 'internal-vpc', 'platform', NULL, '{"tier":"tier-3"}'),
  ('a1000000-0000-4000-8000-000000000006', 'analytics-etl-runner', 'Nightly analytics ETL runner', 'function', 'production', 'internal-vpc', 'data-platform', NULL, '{"tier":"tier-2"}')
ON CONFLICT (asset_id) DO NOTHING;

-- 2) Extra CVEs (varied severity; ON CONFLICT no-op) --------------------------
INSERT INTO cves (cve_id, published_at, description, cvss_score, cvss_vector, severity)
VALUES
  ('CVE-2024-3094',  '2024-03-29T00:00:00Z', 'xz/liblzma upstream backdoor enabling remote unauthenticated SSH access under specific build conditions.', 10.0, 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H', 'CRITICAL'),
  ('CVE-2024-2961',  '2024-04-17T00:00:00Z', 'glibc iconv() out-of-bounds write reachable via crafted ISO-2022-CN-EXT sequences.', 8.1, 'CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:H', 'HIGH'),
  ('CVE-2024-6387',  '2024-07-01T00:00:00Z', 'OpenSSH regreSSHion: signal-handler race enabling unauthenticated RCE as root on glibc-based Linux.', 8.1, 'CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:H', 'HIGH'),
  ('CVE-2023-44487', '2023-10-10T00:00:00Z', 'HTTP/2 Rapid Reset: rapid stream cancellation enables denial of service against HTTP/2 servers.', 7.5, 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H', 'HIGH'),
  ('CVE-2024-5535',  '2024-06-27T00:00:00Z', 'OpenSSL SSL_select_next_proto buffer overread with an empty supported client protocols buffer.', 5.9, 'CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:L/A:L', 'MEDIUM'),
  ('CVE-2023-9876',  '2023-12-01T00:00:00Z', 'Verbose log record parsing allows minor information disclosure in internal log processors.', 4.3, 'CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:N/A:N', 'MEDIUM'),
  ('CVE-2024-24790', '2024-06-04T00:00:00Z', 'Go net/netip mishandles IPv4-mapped IPv6 addresses, permitting access-control bypasses in some apps.', 9.8, 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H', 'CRITICAL'),
  ('CVE-2022-40897', '2022-12-23T00:00:00Z', 'Python setuptools ReDoS via crafted package index HTML during dependency resolution.', 3.7, 'CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:L', 'LOW')
ON CONFLICT (cve_id) DO NOTHING;

-- 3) Asset ↔ CVE links (UNIQUE(asset_id, cve_id); ON CONFLICT no-op) ----------
INSERT INTO asset_cve_links (asset_id, cve_id, detection_source, status)
VALUES
  ('a1000000-0000-4000-8000-000000000001', 'CVE-2024-3094',  'scanner-automated', 'investigating'),
  ('a1000000-0000-4000-8000-000000000002', 'CVE-2024-6387',  'scanner-automated', 'open'),
  ('a1000000-0000-4000-8000-000000000002', 'CVE-2023-44487', 'feed-upstream',     'open'),
  ('a1000000-0000-4000-8000-000000000003', 'CVE-2023-9876',  'scanner-automated', 'resolved'),
  ('a1000000-0000-4000-8000-000000000004', 'CVE-2024-2961',  'scanner-automated', 'investigating'),
  ('a1000000-0000-4000-8000-000000000004', 'CVE-2024-5535',  'scanner-automated', 'open'),
  ('a1000000-0000-4000-8000-000000000005', 'CVE-2022-40897', 'manual-report',     'open'),
  ('a1000000-0000-4000-8000-000000000006', 'CVE-2024-24790', 'scanner-automated', 'open')
ON CONFLICT (asset_id, cve_id) DO NOTHING;

-- 4) Extra findings — the rows the dashboard table renders. -------------------
-- Fixed finding_id UUIDs + stable idempotency_key so re-runs are no-ops.
-- created_at is staggered (newest first in the DESC-ordered table).
INSERT INTO findings (finding_id, cve_id, asset_id, status, proposed_severity, approved_severity, exploitability_score, exploitability_rationale, remediation_priority, sla_due_at, owner_team, decision_state, idempotency_key, created_at)
VALUES
  -- CRITICAL, internet-facing, awaiting review
  ('f0000000-0000-4000-8000-000000000001', 'CVE-2024-3094', 'a1000000-0000-4000-8000-000000000001',
   'investigating', 'CRITICAL', 'CRITICAL', 10.0,
   'Supply-chain backdoor in a transitive build dependency; edge terminator is internet-facing, so exposure must be confirmed before any automated action.',
   'IMMEDIATE', now() + INTERVAL '3 days', 'platform-security', 'manual_review',
   'extra-CVE-2024-3094-edge-tls-terminator', now() - INTERVAL '2 hours'),

  -- CRITICAL, internal, denied (policy blocks auto-remediation window)
  ('f0000000-0000-4000-8000-000000000002', 'CVE-2024-24790', 'a1000000-0000-4000-8000-000000000006',
   'new', 'CRITICAL', NULL, 9.8,
   'IPv4-mapped IPv6 access-control bypass in a Go service; internal exposure limits blast radius but ETL runner touches regulated datasets.',
   'HIGH', now() + INTERVAL '5 days', 'data-platform', 'deny',
   'extra-CVE-2024-24790-analytics-etl-runner', now() - INTERVAL '6 hours'),

  -- HIGH, internet-facing, manual review
  ('f0000000-0000-4000-8000-000000000003', 'CVE-2024-6387', 'a1000000-0000-4000-8000-000000000002',
   'investigating', 'HIGH', 'HIGH', 8.1,
   'regreSSHion RCE reachable on the partner ingress bastion path; exploit is timing-dependent but public tooling exists.',
   'HIGH', now() + INTERVAL '7 days', 'integrations', 'manual_review',
   'extra-CVE-2024-6387-partner-api-ingress', now() - INTERVAL '1 day'),

  -- HIGH, internet-facing, manual review (LB mitigation must be reviewed before rollout)
  ('f0000000-0000-4000-8000-000000000004', 'CVE-2023-44487', 'a1000000-0000-4000-8000-000000000002',
   'new', 'HIGH', 'HIGH', 7.5,
   'HTTP/2 Rapid Reset DoS against the partner ingress; mitigations available at the load-balancer layer.',
   'MEDIUM', now() + INTERVAL '10 days', 'integrations', 'manual_review',
   'extra-CVE-2023-44487-partner-api-ingress', now() - INTERVAL '2 days'),

  -- HIGH, internal, allowed (auto-remediation permitted)
  ('f0000000-0000-4000-8000-000000000005', 'CVE-2024-2961', 'a1000000-0000-4000-8000-000000000004',
   'investigating', 'HIGH', 'HIGH', 8.1,
   'glibc iconv OOB write on internal billing workers; not internet-reachable, standard patch path applies.',
   'MEDIUM', now() + INTERVAL '14 days', 'payments', 'allow',
   'extra-CVE-2024-2961-billing-worker-fleet', now() - INTERVAL '3 days'),

  -- MEDIUM, internal, allowed
  ('f0000000-0000-4000-8000-000000000006', 'CVE-2024-5535', 'a1000000-0000-4000-8000-000000000004',
   'new', 'MEDIUM', NULL, 5.9,
   'OpenSSL buffer overread reachable only with a non-default ALPN configuration; low practical risk internally.',
   'LOW', now() + INTERVAL '21 days', 'payments', 'allow',
   'extra-CVE-2024-5535-billing-worker-fleet', now() - INTERVAL '4 days'),

  -- MEDIUM, internal, resolved
  ('f0000000-0000-4000-8000-000000000007', 'CVE-2023-9876', 'a1000000-0000-4000-8000-000000000003',
   'resolved', 'MEDIUM', 'MEDIUM', 4.3,
   'Verbose log parsing info disclosure on the internal log bus; auto-patched during the routine maintenance window.',
   'LOW', now() - INTERVAL '1 day', 'observability', 'allow',
   'extra-CVE-2023-9876-internal-log-bus', now() - INTERVAL '6 days'),

  -- LOW, development, allowed (no prod exposure -> routine auto-allow)
  ('f0000000-0000-4000-8000-000000000008', 'CVE-2022-40897', 'a1000000-0000-4000-8000-000000000005',
   'new', 'LOW', 'LOW', 3.7,
   'setuptools ReDoS in the dev sandbox toolchain; no production exposure, tracked for hygiene.',
   'LOW', now() + INTERVAL '30 days', 'platform', 'allow',
   'extra-CVE-2022-40897-dev-sandbox-api', now() - INTERVAL '8 days')
ON CONFLICT (idempotency_key) DO NOTHING;

-- 4b) Reconcile findings seeded by an earlier version of this file. --------------
-- Findings #4 (CVE-2023-44487) and #8 (CVE-2022-40897) originally shipped with
-- decision_state='pending'. decisions.decision_score is CHECK-constrained to
-- allow/deny/manual_review, so 'pending' findings could not carry a formal
-- decision row and their Governance card was stuck "unreviewed" — contradicting
-- the dashboard badge. Convert them to concrete states so the whole queue tells
-- a coherent story. Guarded on the old value, so this is a no-op after the first
-- run and never disturbs a manually re-triaged finding.
UPDATE findings
SET decision_state = 'manual_review', approved_severity = 'HIGH'
WHERE finding_id = 'f0000000-0000-4000-8000-000000000004' AND decision_state = 'pending';

UPDATE findings
SET decision_state = 'allow', approved_severity = 'LOW'
WHERE finding_id = 'f0000000-0000-4000-8000-000000000008' AND decision_state = 'pending';

-- 5) Governance decision rows for the extras. ---------------------------------
-- decision_score is set equal to each finding's decision_state so the dashboard
-- governance badge matches the detail-page Governance card. Each proposal_jsonb
-- carries a unique action_id; the decisions table's UNIQUE(action_id) makes this
-- insert idempotent via ON CONFLICT (action_id) DO NOTHING.
INSERT INTO decisions (finding_id, proposal_jsonb, proposed_by, decision_score, decided_by, decided_at, rationale)
VALUES
  -- #1 CVE-2024-3094 — manual_review (supply-chain, internet-facing edge)
  ('f0000000-0000-4000-8000-000000000001',
   jsonb_build_object('action_id','remediate-CVE-2024-3094-edge-tls-terminator','action','patch_package','target','edge-tls-terminator','change','Rebuild image with a verified-clean xz/liblzma and redeploy','severity','CRITICAL','exposure','internet-facing'),
   'zdl_governance', 'manual_review', 'zdl_governance', now() - INTERVAL '110 minutes',
   'DECISION: manual_review. edge-tls-terminator is an internet-facing tier-0 service, matching manual-review-critical-internet. This is a supply-chain backdoor in a transitive build dependency, so exposure to the affected liblzma build must be confirmed by hand before any automated rebuild. Recommended path: verify the installed xz version against the compromised range, rebuild from a known-good base image, and redeploy under change control.'),
  -- #2 CVE-2024-24790 — deny (internal ETL touching regulated data)
  ('f0000000-0000-4000-8000-000000000002',
   jsonb_build_object('action_id','remediate-CVE-2024-24790-analytics-etl-runner','action','patch_package','target','analytics-etl-runner','change','Upgrade Go runtime and rebuild the ETL image','severity','CRITICAL','exposure','internal-vpc'),
   'zdl_governance', 'deny', 'zdl_governance', now() - INTERVAL '5 hours',
   'DECISION: deny. The analytics ETL runner processes regulated datasets, and an in-place automated Go-runtime upgrade during a nightly ETL window risks corrupting an in-flight batch. Auto-remediation is denied; schedule the runtime upgrade after the current batch drains and validate output row counts before re-enabling the pipeline.'),
  -- #3 CVE-2024-6387 — manual_review (regreSSHion on partner ingress)
  ('f0000000-0000-4000-8000-000000000003',
   jsonb_build_object('action_id','remediate-CVE-2024-6387-partner-api-ingress','action','patch_package','target','partner-api-ingress','change','Upgrade OpenSSH to a fixed release and reload sshd','severity','HIGH','exposure','internet-facing'),
   'zdl_governance', 'manual_review', 'zdl_governance', now() - INTERVAL '23 hours',
   'DECISION: manual_review. partner-api-ingress is internet-facing, matching manual-review-critical-internet for high-severity remote-code-execution exposure. regreSSHion is a timing-dependent RCE with public tooling; the sshd restart must be sequenced with partner-traffic draining to avoid dropping in-flight sessions. Recommended path: patch and reload during a coordinated partner maintenance notice.'),
  -- #4 CVE-2023-44487 — manual_review (HTTP/2 Rapid Reset, LB mitigation review)
  ('f0000000-0000-4000-8000-000000000004',
   jsonb_build_object('action_id','remediate-CVE-2023-44487-partner-api-ingress','action','apply_mitigation','target','partner-api-ingress','change','Enable HTTP/2 Rapid Reset protection at the load balancer','severity','HIGH','exposure','internet-facing'),
   'zdl_governance', 'manual_review', 'zdl_governance', now() - INTERVAL '47 hours',
   'DECISION: manual_review. The mitigation is a load-balancer configuration change on an internet-facing ingress; because it alters connection handling for live partner traffic it matches manual-review-critical-internet and must be reviewed before rollout. Recommended path: stage the HTTP/2 stream-reset limits in a canary listener, confirm no legitimate clients are throttled, then promote.'),
  -- #5 CVE-2024-2961 — allow (internal billing, standard patch path)
  ('f0000000-0000-4000-8000-000000000005',
   jsonb_build_object('action_id','remediate-CVE-2024-2961-billing-worker-fleet','action','patch_package','target','billing-worker-fleet','change','Upgrade glibc and rolling-restart the worker fleet','severity','HIGH','exposure','internal-vpc'),
   'zdl_governance', 'allow', 'zdl_governance', now() - INTERVAL '3 days' + INTERVAL '20 minutes',
   'DECISION: allow. The billing worker fleet is internal-vpc and not internet-reachable, so the glibc iconv fix follows the standard automated patch path (allow-noncrit-internal posture). Auto-remediation approved: roll the glibc upgrade through the fleet with a health-checked rolling restart; no change window required.'),
  -- #6 CVE-2024-5535 — allow (internal, non-default ALPN, low risk)
  ('f0000000-0000-4000-8000-000000000006',
   jsonb_build_object('action_id','remediate-CVE-2024-5535-billing-worker-fleet','action','patch_package','target','billing-worker-fleet','change','Upgrade OpenSSL on the billing worker fleet','severity','MEDIUM','exposure','internal-vpc'),
   'zdl_governance', 'allow', 'zdl_governance', now() - INTERVAL '4 days' + INTERVAL '15 minutes',
   'DECISION: allow. The OpenSSL buffer overread is only reachable with a non-default ALPN configuration that these internal workers do not use, and the asset is internal-vpc. Practical risk is low; auto-remediation approved as routine maintenance during the next rolling deploy.'),
  -- #7 CVE-2023-9876 — allow (resolved; auto-patched)
  ('f0000000-0000-4000-8000-000000000007',
   jsonb_build_object('action_id','remediate-CVE-2023-9876-internal-log-bus','action','patch_package','target','internal-log-bus','change','Patch the log-record parser on the internal log bus','severity','MEDIUM','exposure','internal-vpc'),
   'zdl_governance', 'allow', 'zdl_governance', now() - INTERVAL '6 days' + INTERVAL '30 minutes',
   'DECISION: allow. Minor information disclosure in an internal-vpc log processor with no regulated-data exposure. Policy permitted auto-remediation; the agent applied the parser patch during the routine maintenance window and the finding is resolved.'),
  -- #8 CVE-2022-40897 — allow (dev sandbox, no prod exposure)
  ('f0000000-0000-4000-8000-000000000008',
   jsonb_build_object('action_id','remediate-CVE-2022-40897-dev-sandbox-api','action','patch_package','target','dev-sandbox-api','change','Upgrade setuptools in the dev sandbox toolchain','severity','LOW','exposure','internal-vpc'),
   'zdl_governance', 'allow', 'zdl_governance', now() - INTERVAL '8 days' + INTERVAL '25 minutes',
   'DECISION: allow. setuptools ReDoS confined to a development sandbox with no production exposure. Auto-remediation approved for hygiene; bump setuptools on the next sandbox image rebuild.')
ON CONFLICT (action_id) DO NOTHING;

-- 6) Audit timeline for the extras. -------------------------------------------
-- Uses the exact action names the UI color-codes (CREATED, ASSIGNED,
-- STATUS_CHANGED, SEMANTIC_MEMORY_QUERY, POLICY_EVALUATION) plus a policy_check
-- event. action_timeline has no natural unique key, so each finding's block is
-- guarded by NOT EXISTS on that finding_id — re-running this file is a no-op
-- once a finding already has timeline events.
INSERT INTO action_timeline (finding_id, actor_type, actor_id, action, target_table, target_id, payload_json, created_at)
SELECT * FROM (VALUES
  -- #1 CVE-2024-3094 (manual_review)
  ('f0000000-0000-4000-8000-000000000001'::UUID, 'agent', 'zdl_ingest', 'CREATED', 'findings', 'f0000000-0000-4000-8000-000000000001'::UUID, jsonb_build_object('cve_id','CVE-2024-3094','severity','CRITICAL','source','scanner-automated'), now() - INTERVAL '2 hours' - INTERVAL '9 minutes'),
  ('f0000000-0000-4000-8000-000000000001'::UUID, 'agent', 'zdl_supervisor', 'ASSIGNED', 'findings', 'f0000000-0000-4000-8000-000000000001'::UUID, jsonb_build_object('owner_team','platform-security','remediation_priority','IMMEDIATE'), now() - INTERVAL '2 hours' - INTERVAL '8 minutes'),
  ('f0000000-0000-4000-8000-000000000001'::UUID, 'agent', 'zdl_supervisor', 'STATUS_CHANGED', 'findings', 'f0000000-0000-4000-8000-000000000001'::UUID, jsonb_build_object('from','new','to','investigating'), now() - INTERVAL '2 hours' - INTERVAL '7 minutes'),
  ('f0000000-0000-4000-8000-000000000001'::UUID, 'agent', 'zdl_ingest', 'SEMANTIC_MEMORY_QUERY', 'semantic_memory', NULL, jsonb_build_object('top_match_cve','CVE-2024-3094','matches_returned',3), now() - INTERVAL '2 hours' - INTERVAL '5 minutes'),
  ('f0000000-0000-4000-8000-000000000001'::UUID, 'agent', 'zdl_governance', 'POLICY_EVALUATION', 'decisions', 'f0000000-0000-4000-8000-000000000001'::UUID, jsonb_build_object('matched_rules','manual-review-critical-internet','decision','manual_review'), now() - INTERVAL '2 hours' - INTERVAL '3 minutes'),
  ('f0000000-0000-4000-8000-000000000001'::UUID, 'agent', 'zdl_governance', 'policy_check', 'findings', 'f0000000-0000-4000-8000-000000000001'::UUID, jsonb_build_object('matched_rule_name','manual-review-critical-internet','decision','manual_review'), now() - INTERVAL '2 hours' - INTERVAL '3 minutes'),
  -- #2 CVE-2024-24790 (deny)
  ('f0000000-0000-4000-8000-000000000002'::UUID, 'agent', 'zdl_ingest', 'CREATED', 'findings', 'f0000000-0000-4000-8000-000000000002'::UUID, jsonb_build_object('cve_id','CVE-2024-24790','severity','CRITICAL','source','scanner-automated'), now() - INTERVAL '6 hours' - INTERVAL '9 minutes'),
  ('f0000000-0000-4000-8000-000000000002'::UUID, 'agent', 'zdl_supervisor', 'ASSIGNED', 'findings', 'f0000000-0000-4000-8000-000000000002'::UUID, jsonb_build_object('owner_team','data-platform','remediation_priority','HIGH'), now() - INTERVAL '6 hours' - INTERVAL '8 minutes'),
  ('f0000000-0000-4000-8000-000000000002'::UUID, 'agent', 'zdl_ingest', 'SEMANTIC_MEMORY_QUERY', 'semantic_memory', NULL, jsonb_build_object('matches_returned',2), now() - INTERVAL '6 hours' - INTERVAL '6 minutes'),
  ('f0000000-0000-4000-8000-000000000002'::UUID, 'agent', 'zdl_governance', 'POLICY_EVALUATION', 'decisions', 'f0000000-0000-4000-8000-000000000002'::UUID, jsonb_build_object('matched_rules','deny-inflight-regulated-batch','decision','deny'), now() - INTERVAL '6 hours' - INTERVAL '4 minutes'),
  ('f0000000-0000-4000-8000-000000000002'::UUID, 'agent', 'zdl_governance', 'policy_check', 'findings', 'f0000000-0000-4000-8000-000000000002'::UUID, jsonb_build_object('matched_rule_name','manual-review-ephi','decision','deny'), now() - INTERVAL '6 hours' - INTERVAL '4 minutes'),
  -- #3 CVE-2024-6387 (manual_review)
  ('f0000000-0000-4000-8000-000000000003'::UUID, 'agent', 'zdl_ingest', 'CREATED', 'findings', 'f0000000-0000-4000-8000-000000000003'::UUID, jsonb_build_object('cve_id','CVE-2024-6387','severity','HIGH','source','scanner-automated'), now() - INTERVAL '1 day' - INTERVAL '9 minutes'),
  ('f0000000-0000-4000-8000-000000000003'::UUID, 'agent', 'zdl_supervisor', 'ASSIGNED', 'findings', 'f0000000-0000-4000-8000-000000000003'::UUID, jsonb_build_object('owner_team','integrations','remediation_priority','HIGH'), now() - INTERVAL '1 day' - INTERVAL '8 minutes'),
  ('f0000000-0000-4000-8000-000000000003'::UUID, 'agent', 'zdl_supervisor', 'STATUS_CHANGED', 'findings', 'f0000000-0000-4000-8000-000000000003'::UUID, jsonb_build_object('from','new','to','investigating'), now() - INTERVAL '1 day' - INTERVAL '7 minutes'),
  ('f0000000-0000-4000-8000-000000000003'::UUID, 'agent', 'zdl_ingest', 'SEMANTIC_MEMORY_QUERY', 'semantic_memory', NULL, jsonb_build_object('top_match_cve','CVE-2024-1234','matches_returned',2), now() - INTERVAL '1 day' - INTERVAL '5 minutes'),
  ('f0000000-0000-4000-8000-000000000003'::UUID, 'agent', 'zdl_governance', 'POLICY_EVALUATION', 'decisions', 'f0000000-0000-4000-8000-000000000003'::UUID, jsonb_build_object('matched_rules','manual-review-critical-internet','decision','manual_review'), now() - INTERVAL '1 day' - INTERVAL '3 minutes'),
  ('f0000000-0000-4000-8000-000000000003'::UUID, 'agent', 'zdl_governance', 'policy_check', 'findings', 'f0000000-0000-4000-8000-000000000003'::UUID, jsonb_build_object('matched_rule_name','manual-review-critical-internet','decision','manual_review'), now() - INTERVAL '1 day' - INTERVAL '3 minutes'),
  -- #4 CVE-2023-44487 (manual_review)
  ('f0000000-0000-4000-8000-000000000004'::UUID, 'agent', 'zdl_ingest', 'CREATED', 'findings', 'f0000000-0000-4000-8000-000000000004'::UUID, jsonb_build_object('cve_id','CVE-2023-44487','severity','HIGH','source','feed-upstream'), now() - INTERVAL '2 days' - INTERVAL '9 minutes'),
  ('f0000000-0000-4000-8000-000000000004'::UUID, 'agent', 'zdl_supervisor', 'ASSIGNED', 'findings', 'f0000000-0000-4000-8000-000000000004'::UUID, jsonb_build_object('owner_team','integrations','remediation_priority','MEDIUM'), now() - INTERVAL '2 days' - INTERVAL '8 minutes'),
  ('f0000000-0000-4000-8000-000000000004'::UUID, 'agent', 'zdl_ingest', 'SEMANTIC_MEMORY_QUERY', 'semantic_memory', NULL, jsonb_build_object('matches_returned',1), now() - INTERVAL '2 days' - INTERVAL '6 minutes'),
  ('f0000000-0000-4000-8000-000000000004'::UUID, 'agent', 'zdl_governance', 'POLICY_EVALUATION', 'decisions', 'f0000000-0000-4000-8000-000000000004'::UUID, jsonb_build_object('matched_rules','manual-review-critical-internet','decision','manual_review'), now() - INTERVAL '2 days' - INTERVAL '4 minutes'),
  ('f0000000-0000-4000-8000-000000000004'::UUID, 'agent', 'zdl_governance', 'policy_check', 'findings', 'f0000000-0000-4000-8000-000000000004'::UUID, jsonb_build_object('matched_rule_name','manual-review-critical-internet','decision','manual_review'), now() - INTERVAL '2 days' - INTERVAL '4 minutes'),
  -- #5 CVE-2024-2961 (allow)
  ('f0000000-0000-4000-8000-000000000005'::UUID, 'agent', 'zdl_ingest', 'CREATED', 'findings', 'f0000000-0000-4000-8000-000000000005'::UUID, jsonb_build_object('cve_id','CVE-2024-2961','severity','HIGH','source','scanner-automated'), now() - INTERVAL '3 days' - INTERVAL '9 minutes'),
  ('f0000000-0000-4000-8000-000000000005'::UUID, 'agent', 'zdl_supervisor', 'ASSIGNED', 'findings', 'f0000000-0000-4000-8000-000000000005'::UUID, jsonb_build_object('owner_team','payments','remediation_priority','MEDIUM'), now() - INTERVAL '3 days' - INTERVAL '8 minutes'),
  ('f0000000-0000-4000-8000-000000000005'::UUID, 'agent', 'zdl_supervisor', 'STATUS_CHANGED', 'findings', 'f0000000-0000-4000-8000-000000000005'::UUID, jsonb_build_object('from','new','to','investigating'), now() - INTERVAL '3 days' - INTERVAL '7 minutes'),
  ('f0000000-0000-4000-8000-000000000005'::UUID, 'agent', 'zdl_ingest', 'SEMANTIC_MEMORY_QUERY', 'semantic_memory', NULL, jsonb_build_object('matches_returned',2), now() - INTERVAL '3 days' - INTERVAL '5 minutes'),
  ('f0000000-0000-4000-8000-000000000005'::UUID, 'agent', 'zdl_governance', 'POLICY_EVALUATION', 'decisions', 'f0000000-0000-4000-8000-000000000005'::UUID, jsonb_build_object('matched_rules','allow-noncrit-internal','decision','allow'), now() - INTERVAL '3 days' - INTERVAL '3 minutes'),
  ('f0000000-0000-4000-8000-000000000005'::UUID, 'agent', 'zdl_governance', 'policy_check', 'findings', 'f0000000-0000-4000-8000-000000000005'::UUID, jsonb_build_object('matched_rule_name','allow-noncrit-internal','decision','allow'), now() - INTERVAL '3 days' - INTERVAL '3 minutes'),
  -- #6 CVE-2024-5535 (allow)
  ('f0000000-0000-4000-8000-000000000006'::UUID, 'agent', 'zdl_ingest', 'CREATED', 'findings', 'f0000000-0000-4000-8000-000000000006'::UUID, jsonb_build_object('cve_id','CVE-2024-5535','severity','MEDIUM','source','scanner-automated'), now() - INTERVAL '4 days' - INTERVAL '9 minutes'),
  ('f0000000-0000-4000-8000-000000000006'::UUID, 'agent', 'zdl_supervisor', 'ASSIGNED', 'findings', 'f0000000-0000-4000-8000-000000000006'::UUID, jsonb_build_object('owner_team','payments','remediation_priority','LOW'), now() - INTERVAL '4 days' - INTERVAL '8 minutes'),
  ('f0000000-0000-4000-8000-000000000006'::UUID, 'agent', 'zdl_ingest', 'SEMANTIC_MEMORY_QUERY', 'semantic_memory', NULL, jsonb_build_object('matches_returned',1), now() - INTERVAL '4 days' - INTERVAL '6 minutes'),
  ('f0000000-0000-4000-8000-000000000006'::UUID, 'agent', 'zdl_governance', 'POLICY_EVALUATION', 'decisions', 'f0000000-0000-4000-8000-000000000006'::UUID, jsonb_build_object('matched_rules','allow-noncrit-internal','decision','allow'), now() - INTERVAL '4 days' - INTERVAL '4 minutes'),
  ('f0000000-0000-4000-8000-000000000006'::UUID, 'agent', 'zdl_governance', 'policy_check', 'findings', 'f0000000-0000-4000-8000-000000000006'::UUID, jsonb_build_object('matched_rule_name','allow-noncrit-internal','decision','allow'), now() - INTERVAL '4 days' - INTERVAL '4 minutes'),
  -- #7 CVE-2023-9876 (allow, resolved)
  ('f0000000-0000-4000-8000-000000000007'::UUID, 'agent', 'zdl_ingest', 'CREATED', 'findings', 'f0000000-0000-4000-8000-000000000007'::UUID, jsonb_build_object('cve_id','CVE-2023-9876','severity','MEDIUM','source','scanner-automated'), now() - INTERVAL '6 days' - INTERVAL '9 minutes'),
  ('f0000000-0000-4000-8000-000000000007'::UUID, 'agent', 'zdl_supervisor', 'ASSIGNED', 'findings', 'f0000000-0000-4000-8000-000000000007'::UUID, jsonb_build_object('owner_team','observability','remediation_priority','LOW'), now() - INTERVAL '6 days' - INTERVAL '8 minutes'),
  ('f0000000-0000-4000-8000-000000000007'::UUID, 'agent', 'zdl_governance', 'POLICY_EVALUATION', 'decisions', 'f0000000-0000-4000-8000-000000000007'::UUID, jsonb_build_object('matched_rules','allow-noncrit-internal','decision','allow'), now() - INTERVAL '6 days' - INTERVAL '5 minutes'),
  ('f0000000-0000-4000-8000-000000000007'::UUID, 'agent', 'zdl_governance', 'policy_check', 'findings', 'f0000000-0000-4000-8000-000000000007'::UUID, jsonb_build_object('matched_rule_name','allow-noncrit-internal','decision','allow'), now() - INTERVAL '6 days' - INTERVAL '5 minutes'),
  ('f0000000-0000-4000-8000-000000000007'::UUID, 'agent', 'zdl_remediation', 'STATUS_CHANGED', 'findings', 'f0000000-0000-4000-8000-000000000007'::UUID, jsonb_build_object('from','investigating','to','resolved'), now() - INTERVAL '6 days' - INTERVAL '2 minutes'),
  -- #8 CVE-2022-40897 (allow)
  ('f0000000-0000-4000-8000-000000000008'::UUID, 'agent', 'zdl_ingest', 'CREATED', 'findings', 'f0000000-0000-4000-8000-000000000008'::UUID, jsonb_build_object('cve_id','CVE-2022-40897','severity','LOW','source','manual-report'), now() - INTERVAL '8 days' - INTERVAL '9 minutes'),
  ('f0000000-0000-4000-8000-000000000008'::UUID, 'agent', 'zdl_supervisor', 'ASSIGNED', 'findings', 'f0000000-0000-4000-8000-000000000008'::UUID, jsonb_build_object('owner_team','platform','remediation_priority','LOW'), now() - INTERVAL '8 days' - INTERVAL '8 minutes'),
  ('f0000000-0000-4000-8000-000000000008'::UUID, 'agent', 'zdl_ingest', 'SEMANTIC_MEMORY_QUERY', 'semantic_memory', NULL, jsonb_build_object('matches_returned',1), now() - INTERVAL '8 days' - INTERVAL '6 minutes'),
  ('f0000000-0000-4000-8000-000000000008'::UUID, 'agent', 'zdl_governance', 'POLICY_EVALUATION', 'decisions', 'f0000000-0000-4000-8000-000000000008'::UUID, jsonb_build_object('matched_rules','allow-noncrit-internal','decision','allow'), now() - INTERVAL '8 days' - INTERVAL '4 minutes'),
  ('f0000000-0000-4000-8000-000000000008'::UUID, 'agent', 'zdl_governance', 'policy_check', 'findings', 'f0000000-0000-4000-8000-000000000008'::UUID, jsonb_build_object('matched_rule_name','allow-noncrit-internal','decision','allow'), now() - INTERVAL '8 days' - INTERVAL '4 minutes')
) AS v(finding_id, actor_type, actor_id, action, target_table, target_id, payload_json, created_at)
WHERE NOT EXISTS (
  SELECT 1 FROM action_timeline t WHERE t.finding_id = v.finding_id
);

-- 7) Posture-matching prior incidents so every extra's recall card fills. ------
-- The KNN endpoint pre-filters candidates by the finding's own severity +
-- exposure, so these analogs share that metadata. embedding/embedded_at are left
-- NULL — backend/db/seed_embed.py computes real Titan vectors on the next run.
-- Idempotent via UNIQUE (idempotency_key) -> ON CONFLICT DO NOTHING.
INSERT INTO semantic_memory (incident_jsonb, summary, tags, idempotency_key)
VALUES
  -- CRITICAL + internal-vpc — supports #2 (analytics-etl-runner, deny)
  ('{"cve_id":"CVE-2023-4911","asset_name":"batch-scoring-runner","exposure":"internal-vpc","severity":"CRITICAL","decision":"deny","outcome":"denied_inflight_batch","timestamp":"2023-10-12T02:30:00Z"}'::JSONB,
   'glibc "Looney Tunables" (CVE-2023-4911) on batch-scoring-runner: internal critical; governance denied auto-remediation mid-batch and scheduled the glibc upgrade after the pipeline drained.',
   ARRAY['glibc','critical','internal','deny','batch','regulated-data'],
   'extra-mem-CVE-2023-4911-batch-scoring-runner'),
  -- CRITICAL + internal-vpc — second analog for #2
  ('{"cve_id":"CVE-2022-42889","asset_name":"etl-text-normalizer","exposure":"internal-vpc","severity":"CRITICAL","decision":"deny","outcome":"denied_pending_window","timestamp":"2022-10-27T11:05:00Z"}'::JSONB,
   'Text4Shell (CVE-2022-42889) on etl-text-normalizer: internal critical in a data pipeline; auto-remediation denied to protect an in-flight regulated batch, patched in the next window.',
   ARRAY['supply-chain','critical','internal','deny','etl'],
   'extra-mem-CVE-2022-42889-etl-text-normalizer'),
  -- HIGH + internal-vpc — supports #5 (billing-worker-fleet, allow)
  ('{"cve_id":"CVE-2023-4863","asset_name":"invoice-render-fleet","exposure":"internal-vpc","severity":"HIGH","decision":"allow","outcome":"auto-patched","timestamp":"2023-09-20T13:40:00Z"}'::JSONB,
   'libwebp heap overflow (CVE-2023-4863) on invoice-render-fleet: internal high; policy allowed auto-remediation and the agent rolled the patch with a health-checked restart, zero downtime.',
   ARRAY['libwebp','high','internal','allow','auto-patched','billing'],
   'extra-mem-CVE-2023-4863-invoice-render-fleet'),
  -- HIGH + internal-vpc — second analog for #5
  ('{"cve_id":"CVE-2024-0727","asset_name":"payments-signer","exposure":"internal-vpc","severity":"HIGH","decision":"allow","outcome":"auto-patched","timestamp":"2024-01-30T08:15:00Z"}'::JSONB,
   'OpenSSL PKCS12 null-deref (CVE-2024-0727) on payments-signer: internal high; standard automated patch path applied during a rolling deploy.',
   ARRAY['openssl','high','internal','allow','auto-patched','payments'],
   'extra-mem-CVE-2024-0727-payments-signer'),
  -- LOW + internal-vpc — supports #8 (dev-sandbox-api, allow) and low-severity extras
  ('{"cve_id":"CVE-2021-3807","asset_name":"ci-build-agent","exposure":"internal-vpc","severity":"LOW","decision":"allow","outcome":"auto-patched","timestamp":"2021-09-15T17:20:00Z"}'::JSONB,
   'ansi-regex ReDoS (CVE-2021-3807) on ci-build-agent: internal low-severity toolchain issue; auto-remediated on the next image rebuild as routine hygiene.',
   ARRAY['redos','low','internal','allow','toolchain','dev'],
   'extra-mem-CVE-2021-3807-ci-build-agent')
ON CONFLICT (idempotency_key) DO NOTHING;
