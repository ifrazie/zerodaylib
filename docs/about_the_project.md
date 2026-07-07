## Inspiration

We were inspired by how much of vulnerability management still happens through scattered notes, disconnected systems, and reactive triage. We wanted to build something that feels more like a real operating system for security response: one where findings, decisions, and historical context all live in a durable workflow instead of disappearing into inboxes or chat threads.

## What it does

Zero Day Library is a governed multi-agent system for handling vulnerability findings from intake through review and follow-up. It lets teams ingest findings, evaluate them against policy, retrieve similar past incidents from long-term memory, and maintain an audit trail of what happened and why. The experience is designed to make security operations feel more structured, explainable, and repeatable.

## How we built it

We built the project around a practical MVP stack that combines Python, TypeScript, and modern web tooling. The backend uses FastAPI and Python to expose the core tool endpoints and business logic, while the frontend uses Next.js with React and Tailwind CSS for the interactive dashboard experience. We used CockroachDB as the primary database for findings, policy decisions, audit timelines, and semantic memory, and we integrated Amazon Bedrock AgentCore for the multi-agent workflow layer. The system also connects to Bedrock Titan embeddings for semantic memory retrieval and uses a policy-driven architecture to govern actions and decisions.

## Challenges we ran into

The biggest challenge was connecting the different parts of the workflow into something that felt coherent rather than like separate demos. We had to make sure findings, policy evaluation, semantic memory retrieval, and the UI all spoke to the same underlying model. We also had to balance technical ambition with the reality of building a working MVP in a short time window, especially around data modeling and making the demo understandable for a judge or user.

## Accomplishments that we're proud of

We are proud that we built a working end-to-end experience instead of just isolated components. The project now has a real dashboard, a backend that supports the core workflow, stored audit history, policy-based decision logic, and semantic memory retrieval for similar findings. It feels like a believable foundation for a real security operations tool rather than just a prototype.

## What we learned

We learned that governance is just as important as automation. A tool becomes far more useful when it can explain its decisions and preserve a record of them over time. We also learned that memory matters in operational workflows: past incidents are valuable not just for context, but for making future decisions more consistent and informed.

## What's next for Zero Day Library

The next step is to make the system more complete and production-ready by connecting it to live vulnerability feeds, expanding the agent workflows, and improving the decision experience for operators. We would also like to deepen the policy engine, improve the quality of semantic retrieval, and make the interface more tailored for real security teams with richer workflows, permissions, and reporting.