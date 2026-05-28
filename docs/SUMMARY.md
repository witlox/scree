# Scree — Design Summary for Stakeholders

This document is intended for stakeholders who need to understand the project without engaging with the full design conversation or analyst-level specifications. It is deliberately less technical than the analyst-facing documents but does not hide trade-offs or open questions.

If you are reading this and want detail on any decision, see `docs/analysis/design-decisions.md` for the structured ledger, or `docs/analysis/design-conversation.md` for the reasoning.

---

## Executive summary

The organization currently runs Atlassian's stack (Jira, Confluence, Service Desk). Atlassian is moving these products to cloud-only with terms the organization finds extractive in cost and limiting in control. Scree is a custom application layer that, combined with GitLab Ultimate self-managed (already owned), replaces the Atlassian stack with a system the organization controls.

The custom build is scoped to three substantive gaps that GitLab Ultimate does not fill:

1. Knowledge management UI suitable for non-technical users
2. External customer service desk portal
3. Cross-project portfolio and risk aggregation views

Plus foundational pieces: API gateway, permission engine, indexers, integrations with existing systems (Keycloak, Vault, GitLab, O365, Slack), and migration tooling.

The system stores all primary data as markdown files in Git repositories, providing data sovereignty, an auditable history, and partial offline access during outages.

## Why build, not buy

Three options were considered:

1. **Migrate to Atlassian cloud**: accepts vendor pricing and loss of self-managed control
2. **Adopt open-source replacements**: requires evaluating and integrating multiple tools (Plane/OpenProject + Outline/BookStack + Zammad/FreeScout), each with its own data model and integration points
3. **Custom build on top of GitLab Ultimate**: requires engineering investment but produces a system that fits the organization's specific workflow, integrates cleanly with existing infrastructure, and is owned outright

Option 3 was selected because:

- GitLab Ultimate (self-managed) is already owned and provides much of the substrate
- The organization has already invested in GitLab, Keycloak, Vault, and OpenTelemetry
- Custom build is scoped narrowly to gaps GitLab does not fill, not the whole Atlassian stack
- The build team can work together using the same workflow that has produced other systems in the organization (Kiseki, Heddle, etc.)

The decision was not free. Trade-offs are explicit:

- **Engineering investment**: building this is substantial work, even with AI-assisted coding
- **Operational responsibility**: the organization operates the system; outages are the organization's problem to solve
- **Migration risk**: big bang cutover from Atlassian has limited rollback options
- **Long-tail feature requests**: every team has That One Workflow they will eventually request

The team has weighed these and concluded the value of sovereignty, ownership, and fit-to-workflow exceeds the engineering investment and operational responsibility.

## What gets built vs. what gets reused

### Reused from GitLab Ultimate (no custom work)

- Code hosting, code review, CI/CD
- Issues, epics, iterations, milestones, roadmaps for engineering work
- Issue boards, kanban views, project-level planning
- Audit events across the platform
- Compliance frameworks, push rules, branch protection
- Advanced Search (Elasticsearch-backed)
- Repo-level permissions and group hierarchy
- OIDC integration with Keycloak

### Built custom (the Scree application layer)

- **Knowledge management UI**: WYSIWYG markdown editor with templates, draw.io integration, page hierarchy, page-level permissions, macros for common patterns (meeting notes, decisions, action items, summaries). Backed by Git repos.

- **External customer service desk portal**: customer login, ticket submission (web/email/Slack), ticket views, replies, attachments, status tracking. Multi-channel: a customer can contact via email, web portal, or community Slack channel and have one coherent ticket history.

- **Portfolio and risk aggregation views**: cross-project visibility for leadership and RTEs. Risk register that pulls from project-level risk files and surfaces org-level risks. Portfolio dashboards showing PI commitment status, capacity vs load, dependencies.

- **API gateway**: single enforcement point for all permissions. All access goes through this; no bypass paths.

- **Slack integration**: emoji-based ticket creation from chat, slash-command linking of threads to existing tickets, notifications. Snapshot capture only; no ongoing bidirectional sync.

- **Email integration**: O365 via Microsoft Graph for inbound and outbound. Threading preserved via standard email headers.

- **Indexer infrastructure**: hourly batch indexing for cross-project aggregation views, with manual trigger and critical-severity webhook for fast propagation.

- **Migration pipeline**: Jira → Scree tickets, Confluence → Scree docs, Atlassian Service Desk → Scree tickets. Atlassian archive remains read-only.

### Integration with existing systems

- **Keycloak** as the identity provider; OIDC tokens for all auth
- **Vault** for service credentials and signing keys (not user-facing auth)
- **GitLab Ultimate** as the data substrate and code platform
- **O365** as email transport
- **Slack** as chat platform (one public community channel with external customers)
- **OpenTelemetry** for distributed tracing, metrics, and structured logs

## Scope and non-goals

### In scope for v1

- All three substantive pieces above (knowledge management, service desk, portfolio/risk aggregation)
- Migration from current Atlassian instance
- Read access from local Git clones during GitLab outages

### Explicitly not in v1

- Multi-user customer organizations (academic customers are individuals with an institutional org tag for reporting, not a permission boundary)
- Full bidirectional Slack thread/ticket sync
- Per-customer private Slack channels
- Slack Connect with customer organizations
- Federated identity for external customers beyond Keycloak's native capability
- Internationalization
- Fully disconnected operation with conflict-resolved write replay
- Mobile-native applications
- Customer-to-customer direct messaging through Scree

### Acknowledged limitations

- **Email transport dependency on O365**: if O365 is down, email-driven ticket creation stops. The organization does not own this transport; the sovereignty story is weaker for email than for everything else.
- **External customer ticket submission requires multiple online systems**: gateway, GitLab, and O365 must all be available. This is the least resilient operation in the system.
- **Big bang migration has limited rollback**: pre-cutover validation must be thorough; rollback after cutover would be costly.

## Build approach

### Team

Shared ownership across multiple engineers building together with the same workflow. The team uses the diamond workflow established in other projects (analyst → architect → adversary → implementer → auditor → adversary → integrator), with role profiles and structured handoffs between phases.

This addresses the bus-factor risk: any single engineer can be replaced because the architecture, decisions, and rationale are all documented as the project develops.

### Structure

Monorepo containing the API gateway, web frontend, CLI, Slack integration, email integration, indexers, schemas, migration tooling, and deployment configuration. Single source of truth for the data model; atomic cross-layer changes; single CI and deploy pipeline.

### Effort estimation

Time estimates are not provided in this document because they are unreliable for greenfield work. Instead, relative effort estimates against a baseline "docs-frontend spike" unit (a working WYSIWYG markdown editor with API and permission filtering for one resource type):

| Component | Relative effort |
|-----------|----------------|
| Backend API gateway, indexer, permission engine | 3-4× spike |
| Docs frontend (full WYSIWYG, hierarchy, search) | 2-3× spike |
| External customer portal | 4-5× spike |
| Internal admin UIs (planning, risks, agent queues) | 1-2× spike |
| Migration pipelines (Jira and Confluence) | 2× spike each |
| Email integration (O365 Graph) | 1-2× spike |
| Hardening, security review, rollout | 2-3× spike |

The spike itself is the recommended first deliverable. It calibrates the unit and validates the architecture for the highest-uncertainty piece (the WYSIWYG editor and its integration with Git-backed storage and the permission gateway).

If the spike takes longer than expected, the full project estimates scale accordingly. This is a meaningful early signal.

## Risk register

### High-likelihood, high-impact risks

- **Migration curation never finishes**: open-ended content curation has a known failure mode of running indefinitely. *Mitigation*: time-box curation with a hard deadline; non-curated content goes to read-only archive automatically.
- **Permission leakage in aggregation views**: aggregation queries can leak data if not implemented carefully. *Mitigation*: treat the aggregation permission invariant as load-bearing; test exhaustively; defense in depth via separate indexes for sensitive risk categories.
- **External customer portal underdelivers**: customer-facing UIs often need more polish than internal tools. *Mitigation*: explicit narrow scope for v1; deferred features identified explicitly; user testing before cutover.

### Medium risks

- **WYSIWYG editor edge cases (paste from Word, complex tables) frustrate users**: known hard problem in this domain. *Mitigation*: use mature ProseMirror-based library (TipTap or equivalent); user testing during build.
- **Email threading fails for some customer mail clients**: parsing edge cases are abundant. *Mitigation*: use mature email parsing libraries; conservative threading rules; manual merge capability for agents.
- **Big bang cutover reveals migration gaps**: discovered post-cutover. *Mitigation*: thorough pre-cutover validation gates; parallel read access to Atlassian archive during stabilization period.

### Lower risks

- **Vault outage affects service operations**: degrades service-to-service, not user auth. *Mitigation*: standard Vault HA configuration.
- **GitLab Ultimate licensing changes adversely in future**: similar concern to current Atlassian situation but for one product, not three. *Mitigation*: accept this; revisit if and when it occurs.

### Known unknowns flagged for resolution

The following are open questions that need stakeholder input before v1 ships. See `docs/analysis/open-questions.md` for the full list:

- Definition of `severity: critical` for risk webhook triggering
- Minimum feature set for external customer portal
- Pre-cutover validation gates
- Migration curation criteria
- Compliance regime constraints (if any)
- List of paths requiring MR-based update
- Archive strategy (reduced-license vs HTML export)

## Decision authorities

- **Head of Engineering** (executive sponsor): scope cuts, schedule, ratification of stakeholder-input questions, vendor exit timing.
- **Build team**: technical decisions within the constraints in `CLAUDE.md` and the SEED.
- **Compliance/audit** (if engaged): requirements on audit trails, risk register format, data retention.
- **Operations/SRE**: deployment topology, observability requirements, incident response procedures.

## What success looks like

For v1 cutover:

- All teams using Scree for docs, planning, and (where applicable) service desk
- Atlassian archive accessible read-only; new Atlassian licensing not renewed
- External customers using the new portal without dramatic increase in support contact about the portal itself
- Internal users finding the docs UI usable for daily work (the bar: not significantly worse than Confluence for the workflows the team actually uses)
- Audit trail demonstrably complete (any team can produce a history of changes for any resource)

For ongoing operation:

- Operational burden is bounded (incidents handled by the build team or rotating on-call, not constant firefighting)
- New features ship at a sustainable cadence
- Schema and architecture remain coherent (no entropy spiral)

## What is not promised

- That Scree will be feature-parity with Atlassian. Some Confluence macros and Jira features will not be replicated.
- That the migration will be friction-free. Big bang cutovers have costs; the team and stakeholders should expect a transition period.
- That the system will replace social processes. Risk management, planning, and knowledge capture require human discipline that no system provides.
- That AI-assisted coding makes this trivial. AI assistance reduces effort substantially but does not eliminate the operational, integration, and UX work that consumes most of a system's lifecycle cost.

---

**For full technical detail**: see `specs/SEED.md` and the documents in `docs/analysis/`.
**For workflow context**: see `CLAUDE.md` and `.claude/roles/`.
**For open questions**: see `docs/analysis/open-questions.md`.
