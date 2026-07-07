# Tech Stack

Zero Day Librarian uses the following technology stack, selected to satisfy the CockroachDB × AWS Hackathon requirements while building a governed, auditable vulnerability operations system.

## Core Components

### Agent Runtime & Orchestration
- **AWS Bedrock AgentCore** (Harness, Gateway, Lambda MCP targets)
- **Strands Agents** (Python-based agent runtime engine)

### Multi-Agent System
- **zdl_supervisor**: orchestration agent
- **zdl_ingest**: ingests CVE/advisory data
- **zdl_governance**: evaluates policy and determines allow/deny/manual_review outcomes
- **zdl_correlation, zdl_exploitability, zdl_remediation**: specialist agents (optional stretch)

### Backend & Business Logic
- **Python 3.11+** (primary language)
- **FastAPI** for local tool service (reused by Lambda for tool logic)
- **psycopg** (direct SQL connectivity to CockroachDB Cloud)

### Database
- **CockroachDB Cloud (AWS us-east-1)** — serves durable memory, policy state, and audit history
  - `action_timeline`: immutable audit trail
  - `findings`: vulnerability findings with idempotency protection
  - `assets`: production/internet-facing assets
  - `cves`: CVE identifiers and metadata
  - `decisions`: proposals and approval states
  - `policy_rules`: deterministic governance rules (allow/deny/manual_review)
  - `semantic_memory`: prior incidents with vector embeddings stored in a **distributed vector index**

- Required CockroachDB tools used:
  - **CockroachDB Cloud Managed MCP Server** (gateway integrations)
  - **Distributed Vector Indexing** (long-term vulnerability memory retrieval)

### Frontend (post-MVP)
- **Next.js** (dashboard showing findings, governance outcomes, and timeline)

### Infrastructure & IAM
- **AWS IAM Roles & Policies** (scoped harness execution roles; gateway policy; least privilege)
- **AWS Lambda** (MCP target `zdl-tools-handler` backed by FastAPI logic)
- **Terraform/CDK** — infrastructure configurations in repository

### CI/CD & Tooling
- **GitHub Actions** for lint/test/release automation
- **pytest** (tool-level unit tests)
- **Ruff** (Python linting)
- **Mypy** (static type checking)

## Development & Deployment
- **Local-first development** — configure and test backend/tools locally; reuse the same Python logic in AWS Lambda.
- **FastAPI for local testing** of business logic; Lambda serves as a thin MCP tool handler wrapper.
- **psycopg for SQL** — keeps the "CockroachDB SQL tools" story clear and avoids ORM complexity; SQLAlchemy could be added later for more complex logic.

All source code, tool logic, schema, seed data, and prompts are versioned in the repository to enable repeatability and public review, per hackathon requirements.

By leveraging these technologies, ZeroDayLib aims to provide a powerful and flexible toolset for zero-day exploit research and development.