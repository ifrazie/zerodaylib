# Export Notes — zdl_remediationAgent

Scaffolded by copying app/zdl_governanceAgent/ structure (2026).
Adapted: DEFAULT_SYSTEM_PROMPT (remediation persona), memory env var placeholder
(MEMORY_MEMORY_HARNESS_ZDL_REMEDIATION_ID — no memory resource provisioned yet),
pyproject project name.

Status:
- Memory: wired to the pre-existing `harness_zdl_remediation_beb1-44e0wR7Mem`
  memory resource via a `type: memory` connection in `agentcore/agentcore.json`
  (mirrors the pattern used by zdl_supervisorAgent/zdl_ingestAgent/
  zdl_governanceAgent). `memory/session.py` reads
  `MEMORY_MEMORY_HARNESS_ZDL_REMEDIATION_BEB1_44E0WR7MEM_ID`, which `agentcore
  deploy` injects at runtime based on the connection id. Verify this env var
  name against the deployed runtime after the first `agentcore deploy` (it is
  derived from the connection `id` field: uppercase, non-alphanumerics → `_`).
- The shared gateway (zdl-gateway-frkgbxbipc) already exposes the apply_patch_action
  tool via backend/lambda_handler.py; no gateway change needed for this agent to call it.

