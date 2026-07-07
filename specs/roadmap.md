# Roadmap

This roadmap is driven by the CockroachDB × AWS HaKer_fest Hackathon submission deadline. The goal is a polished, functional vertical slice rather than breadth. It directly implements the phases outlined in `ZERO_DAY_LIBRARIAN.md`.

## Phase 1 – Lock Submission Core ✅✂️ (partially done)
**Status:** Gov, Supervisor, Ingest harnesses created; gateway and 3 starter tools deployed; local agents exported; policies reviewed; MVP scope locked to CVE → asset → memory → governance → timeline.
- **[ ]** Freeze MVP scenario and avoid adding more product scope.
- **[ ]** Decide final demo path; leave other agents architecture-only.

## Phase 2 – Real Data Layer (next sprint)
**Status:** `findings`, `action_timeline` tables exist (empty); missing 5 tables.
- **[ ]** Add schema for `assets`, `cves`, `packages`, `asset_cve_links` to support MVP scenario.
- **[ ]** Add `policy_rules` (deterministic allow/deny/manual rules).
- **[ ]** Add `decisions` (proposals/approvals).
- **[ ]** Add `semantic_memory` with **VECTOR column + distributed vector index** (prior incident embeddings).
- **[ ]** Seed: 1 production/internet-facing asset, 1 critical CVE, asset↔cve link, 2–3 prior memory records, sample policy rules.
- **[ ]** Save as `backend/db/schema.sql` and `backend/db/seed.sql` in the repo.
- **[ ]** Validate SQL connectivity from local Python/psycopg.

## Phase 3 – Real Tool Logic (next sprint)
**Status:** Current 3 tools are stubs in Lambda `zdl-tools-handler`; not in repo.
- **[ ]** Create `backend/tools/` Python modules: reusable business logic FastAPI service uses locally and AWS Lambda wraps remotely.
- **[ ]** `timeline_append_event`: append-only writes to `action_timeline`.
- **[ ]** `policy_evaluate_action`: deterministic rule evaluation against `policy_rules`; return allow/deny/manual_review + rationale.
- **[ ]** `finding_create_or_update`: upsert with idempotency key + field-level controls.
- **[ ]** `memory_search_similar` (stretch): vector similarity over `semantic_memory`.
- **[ ]** Add `pytest` tests for each contract; ensure 80%+ coverage.

## Phase 4 – UI (post-sprint)
Show the MVP scenario: Finding detail → Prior memory → Governance outcome → Timeline.
- **[ ]** Findings list view.
- **[ ]** Finding detail view.
- **[ ]** Prior similar cases from `semantic_memory`.
- **[ ]] Show governance decision state.
- **[ ]] Show audit timeline for finding.
- **[ ]] Minimal lightweight dashboard (Next.js or React).

## Phase 5 – Cloud Reintegration
Keep the Lambda thin; reuse local logic rather than reimplement.
- **[ ]** Wrap `backend/tools/**/` in a Lambda handler; keep identical contracts so tools behave the same locally and in cloud.
- **[ ]** Attach gateway only to needed harnesses (supervisor, ingest, governance).
- **[ ]] Validate supervisor and governance flows in AgentCore playground with real DB-backed tools.
- **[ ]] Review IAM roles; enforce least privilege for harnesses/gateways (SQL writes only via gateway tools).

## Phase 6 – Submission Assets
- **[ ]] Polished public README (architecture diagram, screenshots, clear problem statement).
- **[ ]] Configure stable demo URL.
- **[ ]] Scripture 3-minute video demonstrating CVE ingestion → asset link → memory → governance → timeline.
- **[ ]] Prepare Devpost copy (human-written narrative). Ensure judges can open repo and run demo in ≤5m.

## Definition of Done for HaKer_fest
- A judge can open repo and understand problem/workflow/value.
- A judge can open demo and trigger the core scenario.
- The app visibly uses **CockroachDB Cloud Managed MCP Server** and **Distributed Vector Indexing**.
- AWS services are clearly visible in architecture/runtime.
- The video shows problem → workflow → value under 3 minutes.

Once Phase 2–3 are complete, this repo will have a full, auditable, CockroachDB-backed vulnerability workflow, satisfying hackathon requirements.
By following this roadmap, ZeroDayLib aims to become an indispensable resource in the cybersecurity landscape, enabling the responsible discovery and mitigation of zero-day vulnerabilities.