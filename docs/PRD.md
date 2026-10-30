# Product requirements

FlowOps AI is a portfolio-focused operations platform combining lead management, visual workflow definitions, reliable background execution, human approvals and inspected integrations. The complete product requirements are in [REQUIREMENTS.md](REQUIREMENTS.md), with mandatory agent instructions in [CHATGPT.md](../CHATGPT.md).

The target demonstration is lead import → validation/deduplication → deterministic ICP scoring → structured AI draft → human approval → configured or explicitly simulated email delivery → inspectable execution history. This flow is implemented and demonstrated with explicitly labelled mock AI/email providers. A separate real integration reads public GitHub repository metadata.

The application provides accounts, workspaces/roles, lead operations, workflow editing/execution, approvals, integrations, audit history and API-backed analytics. Follow [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md) for actual feature and verification status. No deployment or performance target is claimed before measurement.
