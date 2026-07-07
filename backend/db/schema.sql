-- Database schema for Zero Day Librarian (CockroachDB Cloud / AWS us-east-1)
-- This file defines the target tables for the 'zdl_db' database.
-- Two tables (action_timeline, findings) already exist and are preserved as-is.
-- The remaining 5 MVP tables are defined below.

-- 1) Assets
CREATE TABLE IF NOT EXISTS assets (
    asset_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name STRING NOT NULL,
    description STRING,
    asset_type STRING NOT NULL, -- e.g., 'server', 'container', 'load_balancer', 'function'
    environment STRING NOT NULL, -- 'production', 'staging', 'development'
    exposure STRING NOT NULL, -- 'internet-facing', 'internal-vpc', 'on-premise'
    owner_team STRING,
    ipv4 STRING, -- nullable; many assets lack static public IP
    fqdn STRING, -- nullable; may not exist for compute-only resources
    tags JSONB DEFAULT '{}'::JSONB, -- optional key/value tags
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2) CVE identifiers and basic metadata
CREATE TABLE IF NOT EXISTS cves (
    cve_id STRING PRIMARY KEY, -- e.g., 'CVE-2024-1234'
    published_at TIMESTAMPTZ,
    description STRING,
    cvss_score FLOAT8, -- 0.0-10.0 score
    cvss_vector STRING, -- e.g., 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H'
    severity STRING, -- e.g., 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    affected_packages JSONB, -- list of {name, version_range, ecosystem}
    reference_urls JSONB, -- URLs, advisories, reports
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 3) Packages (optional for asset CVE mapping; stretch)
CREATE TABLE IF NOT EXISTS packages (
    package_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name STRING NOT NULL,
    version STRING NOT NULL,
    ecosystem STRING NOT NULL, -- e.g., 'npm', 'PyPI', 'maven', 'deb', 'rpm', 'nuget'
    asset_id UUID NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
    installed_path STRING, -- optional filesytem path
    is_direct_dependency BOOLEAN DEFAULT false,
    UNIQUE (asset_id, name, version, ecosystem)
);

-- 4) Link table: asset ↔ cve
CREATE TABLE IF NOT EXISTS asset_cve_links (
    link_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
    cve_id STRING NOT NULL REFERENCES cves(cve_id) ON DELETE CASCADE,
    detection_source STRING, -- 'scanner-automated', 'manual-report', 'feed-upstream'
    detected_at TIMESTAMPTZ DEFAULT now(),
    status STRING DEFAULT 'open', -- 'open', 'investigating', 'false-positive', 'resolved'
    UNIQUE (asset_id, cve_id)
);

-- 5) Policy rules (deterministic allow/deny/manual_review)
CREATE TABLE IF NOT EXISTS policy_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name STRING NOT NULL UNIQUE,
    description STRING NOT NULL,
    predicate_json JSONB NOT NULL, -- structured predicate over attributes (e.g., exposure='internet-facing' and severity='CRITICAL')
    decision STRING NOT NULL CHECK (decision IN ('allow', 'deny', 'manual_review')),
    rationale STRING, -- human-readable reason
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 6) Decisions (proposals and approvals)
CREATE TABLE IF NOT EXISTS decisions (
    decision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id UUID REFERENCES findings(finding_id) ON DELETE SET NULL,
    proposal_jsonb JSONB NOT NULL, -- structured proposal including action type, target, intended change
    proposed_by STRING NOT NULL, -- harness name (e.g., 'zdl_governance')
    proposed_at TIMESTAMPTZ DEFAULT now(),
    decision_score STRING CHECK (decision_score IN ('allow', 'deny', 'manual_review')),
    decided_by STRING, -- human user or harness name
    decided_at TIMESTAMPTZ,
    rationale STRING,
    -- computed column extracts action_id from proposal for idempotency
    action_id STRING AS (proposal_jsonb->>'action_id') STORED,
    UNIQUE (action_id) -- idempotency via proposal action_id
);

-- 7) Semantic memory: prior incidents with vector embeddings
-- Use the CockroachDB vector column type and create a distributed vector index --
-- to satisfy the hackathon "Distributed Vector Indexing" requirement.
-- We use Bedrock Titan Embeddings Text v2 (1024-dimensional vector) as the embedding source.
CREATE TABLE IF NOT EXISTS semantic_memory (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_jsonb JSONB NOT NULL, -- full incident data or extrinsic context
    summary STRING NOT NULL, -- TLDR text of the event/incident
    tags STRING[], -- key terms for filtering
    -- vector column for distributed vector index
    embedding VECTOR(1024),
    -- NULL until a real Titan embedding has been computed and stored;
    -- backend/db/seed_embed.py stamps this on refresh so the process is
    -- idempotent (already-embedded rows are skipped on re-run).
    embedded_at TIMESTAMPTZ,
    -- Optional idempotency key for agent-written memories (memory_store tool);
    -- a stable hash of summary + cve_id prevents duplicate memories from
    -- repeated runs. NULL for seeded rows.
    idempotency_key STRING,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (idempotency_key)
);

-- Distributed vector index on memory embeddings (required for hackathon)
CREATE VECTOR INDEX IF NOT EXISTS idx_memory_embedding ON semantic_memory (embedding);

-- Migrations for clusters where semantic_memory already existed before these
-- columns were introduced (CREATE TABLE IF NOT EXISTS above is a no-op against
-- pre-existing tables, so the columns must be added explicitly).
ALTER TABLE semantic_memory ADD COLUMN IF NOT EXISTS embedded_at TIMESTAMPTZ;
ALTER TABLE semantic_memory ADD COLUMN IF NOT EXISTS idempotency_key STRING;
-- CockroachDB supports IF NOT EXISTS on unique indexes; this backs the
-- UNIQUE (idempotency_key) constraint on already-deployed clusters.
CREATE UNIQUE INDEX IF NOT EXISTS semantic_memory_idempotency_key_key
    ON semantic_memory (idempotency_key);

-- Optional helpful indexes
CREATE INDEX IF NOT EXISTS idx_findings_asset ON findings(asset_id);
CREATE INDEX IF NOT EXISTS idx_findings_cve ON findings(cve_id);
CREATE INDEX IF NOT EXISTS idx_findings_decision ON findings(decision_state);
CREATE INDEX IF NOT EXISTS idx_timeline_finding ON action_timeline(finding_id);
CREATE INDEX IF NOT EXISTS idx_assets_environment ON assets(environment);
CREATE INDEX IF NOT EXISTS idx_assets_exposure ON assets(exposure);
