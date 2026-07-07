# Mission

Zero Day Librarian is a governed multi-agent vulnerability operations system built for the CockroachDB × AWS Hackathon. The mission is to turn vulnerability management into persistent, auditable agent workflows backed by durable memory and deterministic policy, rather than treating each CVE as a one-off event.

Instead of volatile, memory-less bots, Zero Day Librarian uses CockroachDB Cloud as the system of record for findings, decisions, policy rules, and an immutable action timeline. Agents retrieve relevant prior incidents from long-term semantic memory to ensure decisions are informed by historical context and governance rules. All state transitions and high-risk actions are mediated by deterministic policy evaluation and recorded in an append-only audit log.

Through this governed autonomy posture, Zero Day Librarian enables security teams to triage and govern high-risk vulnerabilities with durable, explainable agent workflows, establishing reliable governance and auditability down to the database layer.