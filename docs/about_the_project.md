## Inspiration

We were inspired by how much of vulnerability management still happens through scattered notes, disconnected systems, and reactive triage. We wanted to build something that feels more like a real operating system for security response: one where findings, decisions, and historical context all live in a durable workflow instead of disappearing into inboxes or chat threads.

## What it does

Zero Day Library is a governed multi-agent system for handling vulnerability findings from intake through review, remediation, and follow-up. It lets teams ingest findings, evaluate them against policy, retrieve similar past incidents from long-term memory, apply the remediations governance has explicitly approved, and maintain an audit trail of what happened and why. A dedicated remediation agent is the final step in the pipeline: it only acts on findings governance has marked `allow`, and a server-side guardrail refuses `manual_review` or `deny` findings even if asked — the model's judgment is never the thing standing between a decision and an action. The experience is designed to make security operations feel more structured, explainable, and repeatable.

## How we built it

We built the project around a practical MVP stack that combines Python, TypeScript, and modern web tooling. The backend uses FastAPI and Python to expose the core tool endpoints and business logic, while the frontend uses Next.js with React and Tailwind CSS for the interactive dashboard experience. We used CockroachDB as the primary database for findings, policy decisions, audit timelines, and semantic memory, and we integrated Amazon Bedrock AgentCore for four cooperating agents — ingestion, governance, supervision, and remediation — each with its own persistent memory session behind a shared MCP gateway. The system also connects to Bedrock Titan embeddings for semantic memory retrieval and uses a policy-driven architecture to govern actions and decisions, with the remediation agent's own tool enforcing the allow-only rule server-side rather than trusting the model to honor it.

## Challenges we ran into

The biggest challenge was connecting the different parts of the workflow into something that felt coherent rather than like separate demos. We had to make sure findings, policy evaluation, semantic memory retrieval, and the UI all spoke to the same underlying model. We also had to balance technical ambition with the reality of building a working MVP in a short time window, especially around data modeling and making the demo understandable for a judge or user.

One specific, humbling one: while wiring up the remediation agent we discovered that every agent-to-tool call routed through the live AgentCore Gateway had actually been silently failing since the gateway was first stood up. The Lambda handler was reading the invoked tool's name from a Lambda context attribute that AgentCore Gateway never populates — it actually delivers the tool name through Lambda's client-context custom metadata channel, a detail that isn't obvious from the SDK surface. The failure mode was sneaky: the MCP layer still reported the tool call as `"status": "success"` back to the model, so nothing looked broken from the outside. Finding and fixing that turned into a real audit of whether the "agent writes to CockroachDB" story was actually true end-to-end, not just true in the unit tests.

## Accomplishments that we're proud of

We are proud that we built a working end-to-end experience instead of just isolated components. The project now has a real dashboard, a backend that supports the core workflow, stored audit history, policy-based decision logic, semantic memory retrieval for similar findings, and a remediation agent that closes the loop by acting on governance's decision rather than just recording it. It feels like a believable foundation for a real security operations tool rather than just a prototype.

## What we learned

We learned that governance is just as important as automation. A tool becomes far more useful when it can explain its decisions and preserve a record of them over time. We also learned that memory matters in operational workflows: past incidents are valuable not just for context, but for making future decisions more consistent and informed.

## What's next for Zero Day Library

The next step is to make the system more complete and production-ready by connecting it to live vulnerability feeds, expanding beyond simulated remediation to real infrastructure actions behind the same allow-only guardrail, and improving the decision experience for operators. We would also like to deepen the policy engine, improve the quality of semantic retrieval, and make the interface more tailored for real security teams with richer workflows, permissions, and reporting.
