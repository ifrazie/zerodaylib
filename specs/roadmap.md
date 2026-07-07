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

## Phase 3 – Real Tool Logic ✅ (done)
**Status:** All 4 tools implemented in `backend/tools/` as reusable business logic (local FastAPI + AWS Lambda wrap). 10 pytest tests pass against live CockroachDB Cloud `zdl_db` at 90% coverage.
- **[x]** Create `backend/tools/` Python modules: reusable business logic FastAPI service uses locally and AWS Lambda wraps remotely.
- **[x]** `timeline_append_event`: append-only writes to `action_timeline`.
- **[x]** `policy_evaluate_action`: deterministic rule evaluation against `policy_rules`; return allow/deny/manual_review + rationale.
- **[x]** `finding_create_or_update`: upsert with idempotency key + field-level controls.
- **[x]** `memory_search_similar` (stretch): vector similarity over `semantic_memory`.
- **[x]** Add `pytest` tests for each contract; ensure 80%+ coverage (achieved 90%).

## Phase 4 – UI ✅ (done)
Show the MVP scenario: Finding detail → Prior memory → Governance outcome → Timeline.
**Status:** Next.js 14 dashboard builds clean and is wired to the FastAPI backend against live CockroachDB. Findings list + detail render the seeded CVE-2024-7169 scenario; semantic memory uses the real distributed vector index (KNN via `memory_search_similar`); governance resolves `manual_review` from policy rules; audit timeline shows the `policy_check` event. All 5 API endpoints verified end-to-end.
- **[x]** Findings list view.
- **[x]** Finding detail view.
- **[x]** Prior similar cases from `semantic_memory` (real distributed vector KNN, not mock scores).
- **[x]** Show governance decision state.
- **[x]** Show audit timeline for finding.
- **[x]** Minimal lightweight dashboard (Next.js).

## Phase 5 – Cloud Reintegration (authored — ready to deploy)
Keep the Lambda thin; reuse local logic rather than reimplement.
- **[x]** Wrap `backend/tools/**/` in a Lambda handler (`backend/lambda_handler.py`); keep identical contracts (dispatches to unchanged tool functions; tested live against CockroachDB Cloud).
- **[x]** Tool input schemas authored (`backend/tools/schemas/*.json`); tool definitions inline-ready for `create-gateway-target`.
- **[x]** IAM trust + inline policy authored (`backend/iam/zdl-tools-handler-*.json`); least-privilege (Secrets Manager, Titan, CloudWatch Logs only).
- **[x]** Packaging scripts authored (`backend/package_lambda.sh` + `package_lambda.ps1`); handler zip tested and builds clean (16 KB).
- **[x]** Full deploy runbook authored (`docs/DEPLOY.md`) covering: secret, IAM role, layer, Lambda, CockroachDB allowlist, gateway target registration, embed_titan refresh, e2e validation, rollback.
- **[x]** `agentcore.json` kept clean — gateway/memories remain as external connections (correct model; validated with `agentcore validate`).
- **[ ]** **YOU RUN:** Execute `docs/DEPLOY.md` steps 1–9 to deploy Lambda, register gateway target, and validate agent-triggered DB writes.
- **[ ]** Attach gateway only to needed runtimes (supervisor, ingest, governance) — already wired via existing `connections[]`.
- **[ ]** Validate supervisor and governance flows in AgentCore playground with real DB-backed tools (Step 9b in runbook).
- **[ ]** Add deployment target to `agentcore/aws-targets.json` and run `agentcore deploy` for the 3 runtimes.

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