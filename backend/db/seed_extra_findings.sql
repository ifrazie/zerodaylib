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
-- (manual_review/allow/deny/pending) across a mix of internet-facing and
-- internal assets, so the Findings Dashboard table reads as a populated queue.

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

  -- HIGH, internet-facing, pending triage
  ('f0000000-0000-4000-8000-000000000004', 'CVE-2023-44487', 'a1000000-0000-4000-8000-000000000002',
   'new', 'HIGH', NULL, 7.5,
   'HTTP/2 Rapid Reset DoS against the partner ingress; mitigations available at the load-balancer layer.',
   'MEDIUM', now() + INTERVAL '10 days', 'integrations', 'pending',
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

  -- LOW, development, pending
  ('f0000000-0000-4000-8000-000000000008', 'CVE-2022-40897', 'a1000000-0000-4000-8000-000000000005',
   'new', 'LOW', NULL, 3.7,
   'setuptools ReDoS in the dev sandbox toolchain; no production exposure, tracked for hygiene.',
   'LOW', now() + INTERVAL '30 days', 'platform', 'pending',
   'extra-CVE-2022-40897-dev-sandbox-api', now() - INTERVAL '8 days')
ON CONFLICT (idempotency_key) DO NOTHING;
