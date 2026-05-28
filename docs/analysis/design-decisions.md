# Scree — Design Decisions

Structured ledger of decisions made during design conversation. Each entry records what was decided, why, what was rejected, what is deferred, and what consequences follow. The format is uniform to support traceability.

This is not an ADR set (those come from the architect with implementation-specific detail). This is the analyst's input: the design-time decisions that constrain the architecture without specifying it.

---

## DD-001: Build a custom layer on top of GitLab Ultimate rather than replacing it

**Decision**: Reuse GitLab Ultimate for everything it does well. Build custom only for the gaps it does not fill.

**Rationale**: GitLab Ultimate (self-managed, already owned) provides issues, epics with multi-level hierarchy, iterations, roadmaps, advanced search (Elasticsearch-backed), audit events, compliance frameworks, repo permissions, service desk (basic), wiki (engineer-adequate), and many more capabilities. Rebuilding any of these is wasted effort. The custom build narrows to the three substantive gaps: knowledge management UX for non-technical users, external customer service desk portal, and cross-project portfolio and risk aggregation.

**Alternatives rejected**:
- Building Confluence/Jira/Service Desk replacements from scratch: rejected because Ultimate provides the substrate; building from scratch ignores investment already made and creates a much larger project.
- Migrating to cloud Atlassian and accepting cost: rejected per organizational sovereignty preference and cost concerns.

**Consequences**:
- The custom layer is integration-heavy with GitLab APIs.
- GitLab Ultimate licensing remains a cost; the project does not eliminate vendor dependency, only reduces it and changes its character (GitLab is more aligned with self-hosted operation).
- If GitLab significantly changes pricing or licensing in the future, the organization faces a similar decision again — but for one product rather than three.

**Deferred**: None.

---

## DD-002: Primary data stored as markdown with YAML frontmatter in Git repositories

**Decision**: All primary resources (docs, tickets, risks, planning items) are stored as markdown files with YAML frontmatter, in GitLab repositories.

**Rationale**:
- Sovereignty: the organization controls the data substrate. No vendor database lock-in.
- Audit trail: Git history is tamper-evident by construction. Every change has author, timestamp, content delta.
- Operability: standard Unix tooling (`grep`, `awk`, IDEs, language servers) works against the data.
- Partial offline access: local clones provide read access during outages.
- Distributed by nature: backups are clones; multiple clones provide natural redundancy.
- Composability: same data substrate for all resource types simplifies cross-cutting concerns.

**Alternatives rejected**:
- Relational database as primary store: rejected because it sacrifices the sovereignty/audit/operability properties. Derived index in a DB is fine; primary store is not.
- Per-resource-type storage choices (DB for tickets, files for docs): rejected because it complicates cross-cutting concerns (permissions, audit, schema evolution) without proportional benefit.

**Consequences**:
- Querying structured data against Git is slow without an index. Derived indexes (search, aggregation) are required.
- Conflict resolution for structured fields requires care; textual merge of YAML is fallible.
- Permission model must be layered on top because Git's native permissions are coarse (repo-level).
- Schema versioning must be designed in from the start; retrofitting is painful.
- File system performance for large numbers of files in a single directory must be considered (sharding strategies).

**Deferred**:
- Detailed conflict resolution semantics for offline writes (deferred to v2; v1 does not support offline writes for ticket creation).
- Specific schema evolution mechanism (analyst to specify; architect to implement).

---

## DD-003: Partial offline operation — read access yes, ticket creation no

**Decision**: "Run locally during outages" means graceful degradation:
- Read access from local clones: yes
- Edit existing resources with conflict resolution on reconnect: yes (for resources where textual merge works)
- Create new tickets/issues during outage: no (requires GitLab)
- External user ticket submission during outage: no (requires multiple online systems)

**Rationale**: Full disconnected operation with conflict-resolved replay for structured data is a substantial engineering undertaking (CRDT-style field-level merge semantics, queue-and-replay infrastructure, divergence detection). For an organization that primarily needs *resilience* and *sovereignty*, not full offline operation, the trade-off favors simpler implementation with honest scope limits.

**Alternatives rejected**:
- Full offline operation with CRDT-based merge: rejected as over-scoped for v1. The cost is high; the value is incremental over the read-access guarantee.
- Claiming "fully offline-capable" without implementing it: rejected as dishonest.

**Consequences**:
- The "run locally during outages" property is real but narrower than the original framing suggested. Stakeholders must understand the scope.
- External customer ticket submission has multiple online dependencies (gateway, GitLab, O365) and is the least resilient operation.

**Deferred**: Possible v2 enhancement: offline write queue with conflict resolution. Not committed to.

---

## DD-004: Project-level risks in project repos; org-level risks in dedicated repos

**Decision**: Project-scoped risks live in the project repo at `risks/`. Org-level risks (portfolio, ART, strategic, security, compliance) live in dedicated repos with their own permission boundaries.

**Rationale**:
- Risk lives where the work happens, except when the audience is broader than the work.
- Permission inheritance from GitLab repo/group structure is natural and avoids a new authorization layer for the common case.
- Lifecycle matches naturally: project risks die when the project is archived; org risks have independent lifecycles.
- Escalation is explicit: when a project risk needs org visibility, create a corresponding org-level risk with cross-reference. The duplication is intentional — it forces a deliberate "this matters at org level" decision.

**Alternatives rejected**:
- Single global risk graph with relationship modeling: deferred. The pragmatic split is sufficient for current organization scale. Graph can emerge later if needed.
- All risks in a central repo with application-level permissions: rejected because it duplicates a permission model that GitLab already provides correctly.

**Consequences**:
- No automatic detection of unrelated teams sharing the same underlying risk (e.g., two teams depending on the same vendor). Social network catches this at current scale; could become a problem at 10x scale.
- Cross-project aggregation requires an indexer (the "scraper").
- Risk schema must be uniform across project and org repos to enable aggregation.

**Deferred**:
- Graph-based risk relationship modeling.
- Cross-org risk correlation analytics.

---

## DD-005: Indexing trigger model — hourly batch + manual + critical-only webhook

**Decision**: Aggregation indexers run on three triggers:
1. **Hourly batch**: default cadence. Walks all accessible projects, updates the index.
2. **Manual trigger**: authenticated users can request an immediate scrape of a specific project or all projects.
3. **CRITICAL severity webhook**: GitLab webhooks fire on changes touching resources tagged `severity: critical`, triggering immediate indexing of that resource only.

**Rationale**: Inverts the cost/benefit of webhooks correctly. Webhooks are operationally expensive (missed deliveries, retry logic, dead-letter handling, debugging). Latency matters only for a small subset of changes (critical risks needing leadership awareness in minutes). Most changes can tolerate up-to-an-hour latency. Manual trigger handles the "I just updated this, why isn't it showing" friction without requiring webhooks for everything.

**Degradation paths**:
- Webhooks fail → batch catches changes within the hour.
- Batch fails → manual trigger still works; webhooks still work for critical.
- Manual trigger fails → batch still works.

All three would need to fail simultaneously for an indexing outage.

**Alternatives rejected**:
- Webhooks for all changes: rejected as over-engineered for non-critical updates.
- Batch only: rejected because critical risks need faster propagation than hourly.
- Real-time event streaming: rejected as architecturally heavier than needed for the actual access pattern.

**Consequences**:
- The `severity: critical` field becomes load-bearing. Definition must be precise and disciplined.
- Manual trigger endpoint needs proper authentication and rate limiting (anyone-can-trigger is a denial-of-service vector).
- Webhook handler is a separate concern from batch indexer; both must produce consistent results.

**Deferred**: Specific severity-level definitions (analyst to propose; head of engineering to ratify).

---

## DD-006: Single API gateway as sole enforcement point for permissions

**Decision**: All user-facing operations go through the API gateway. Frontend, CLI, Slack integration, and email integration call the same API. The gateway is the only path; no integration has privileged backend access.

**Rationale**:
- Eliminates bypass paths. Permission logic exists in one place. Cannot be circumvented by alternative routes.
- Auditable: all access logged uniformly.
- Testable: permission tests cover the single enforcement layer rather than every integration point.
- Composable: new integration paths (mobile app, automation, third-party) plug in without expanding the trusted surface.

**Alternatives rejected**:
- Per-integration permission enforcement: rejected because permission logic drifts between paths and bugs become bypass paths.
- Direct GitLab API access from frontend: rejected because the custom permission model (ticket relations) cannot be enforced at GitLab's level.

**Consequences**:
- Gateway is the critical path for everything. Its availability, performance, and correctness are central.
- Integration services must call the gateway with proper identity propagation, not service-account-as-everyone.
- Gateway must be hardened, observable, and operated as a tier-1 service.

**Deferred**: Specific gateway implementation (architect decision: language, framework, deployment topology).

---

## DD-007: Permission model layered — GitLab repo-level + application-level ReBAC for service desk

**Decision**:
- Most resources inherit permissions from GitLab repo/group membership (coarse-grained, authoritative).
- Service desk tickets use application-level relationship-based access control (ReBAC) for fine-grained relations (requester, watcher, assignee, owner).
- Aggregation queries filter results at query time by the requester's authority over each item.

**Rationale**:
- GitLab's permission model is well-tested and handles the common case (who can read which repos).
- Service desk tickets have permission rules that don't map to repo membership: "the requester of this ticket can see it; other customers cannot." This is naturally ReBAC.
- Filtering at query time rather than maintaining per-user index partitions is simpler and keeps the index unified.

**Alternatives rejected**:
- Pure application-level permissions for everything: rejected because it duplicates GitLab's correct implementation.
- Repo-per-ticket for service desk: rejected because at 2000-3000 external users with many tickets each, the repo count explodes.

**Consequences**:
- Permission engine (SpiceDB, OpenFGA, or custom) is a substantive component.
- Aggregation queries are slower than naive queries (must check permissions per result).
- Permission cache is needed for performance; cache invalidation is a known hard problem.
- Tests must explicitly cover edge cases (permission changes mid-session, mid-query, etc.).

**Deferred**:
- Specific ReBAC implementation (SpiceDB vs OpenFGA vs custom; architect decision).
- Cache invalidation strategy.

---

## DD-008: Aggregation view permission invariant treated as load-bearing

**Decision**: A user accessing an aggregation view (cross-project risk register, portfolio dashboard, search across docs) never sees data they could not see by accessing the source resource directly. This invariant is treated as load-bearing — a leak here is a serious security failure.

**Rationale**: Aggregation views are the most likely place for permission leaks. The temptation to "show approximate results for performance" is a leak. Pre-filtered indexes per user are an operational nightmare. The correct approach is to query the index broadly and filter results by the requester's authority on each item.

**Specific defenses**:
- Permission check on every item in every aggregation result, not just at view-load time.
- Permission cache short TTL (minutes, not hours) so revocations propagate quickly.
- Audit log of all aggregation queries with user identity and items returned.
- Test suite specifically targeting permission edge cases on aggregation views.
- Sensitive risk categories (security, key-person, M&A) stored in separate indexes from the main index, providing belt-and-suspenders protection.

**Alternatives rejected**:
- Trusting the index to be correctly partitioned by permissions: rejected because index partitioning across many overlapping permission scopes is error-prone.
- "Show counts but not contents" partial results: considered but rejected because counts themselves can be information leaks.

**Consequences**:
- Aggregation query latency includes permission checks; performance work is needed.
- Test suite for permission edge cases is non-trivial to write but is mandatory.
- Caching strategy must balance performance with revocation freshness.

**Deferred**: Specific permission cache implementation; specific test framework.

---

## DD-009: Update model — direct commit default, MR-required for compliance-tagged paths

**Decision**: Most resource updates use direct commit to main. Merge requests are required for an explicit small set of paths/resources:
- Compliance-tagged resources (any resource marked as subject to compliance review)
- Closed risks (preventing silent revision of historical record)
- Doc paths designated for formal review (e.g., HR policy, security policies)

Enforcement: CODEOWNERS, branch protection, and push rules.

**Rationale**:
- Direct commit matches the actual workflow for high-volume routine updates (ticket status changes, doc edits, risk updates).
- MR friction is appropriate for low-volume high-stakes changes (compliance content, historical record integrity).
- Single enforcement mechanism (GitLab's existing branch protection and CODEOWNERS) avoids building a custom approval workflow.

**Alternatives rejected**:
- MR required for everything: rejected as too much friction for routine updates; agents updating ticket status should not need code review.
- Direct commit for everything: rejected because compliance and audit teams need review evidence for specific resource types.
- Custom approval workflow in the application: rejected because GitLab provides this and the custom-built alternative would duplicate it.

**Consequences**:
- The list of MR-required paths must be configured explicitly and maintained.
- New resource types or paths require deciding their update model.
- Compliance ratification of which paths require review is needed.

**Deferred**: Specific list of compliance-tagged paths (head of engineering and compliance to ratify).

---

## DD-010: Monorepo structure for custom layer

**Decision**: Single Git repository contains the custom layer's API gateway, web frontend, CLI, Slack integration, email integration, indexers, schemas, deployment configuration, and migration tooling.

**Rationale**:
- Shared schemas between API, frontend, and CLI: single source of truth for data model.
- Atomic cross-layer changes: adding a field touches schema, API, and frontend in one MR.
- Single CI and deploy pipeline: simpler operationally.
- Bus factor: all engineers see all code; supports team build and shared ownership.
- Refactoring across layers: feasible without coordination across repos.

**Alternatives rejected**:
- Multi-repo with shared library for schemas: rejected because schema changes require coordinated deploys across repos. Monorepo eliminates this.
- Separate repos per service: rejected as over-engineering for the project's scale and team size.

**Consequences**:
- Repo grows over time; build performance must be managed (Nx, Turborepo, or equivalent if needed).
- Permission model within the repo (who can change what) handled via CODEOWNERS.
- Deployment must handle multi-artifact builds from a single source.

**Deferred**: Specific monorepo tooling (architect decision).

---

## DD-011: External customer model — individuals with org tag, no multi-user customer organizations in v1

**Decision**: External customers are modeled as individuals. Each customer is their own account with their own tickets. An "org tag" field captures institutional affiliation as metadata for reporting and analytics. The org tag is *not* a permission boundary in v1: tickets belong to the individual requester; sharing is by explicit per-user grant.

**Rationale**:
- Academic customer population: researchers operate substantially as individuals. Institution-wide ticket visibility is not a common requirement.
- Permission model simplicity: ticket access is requester + explicitly named watchers; no institutional inheritance.
- Architecture preserves option for future: the org tag exists in the schema and can become a permission boundary later without data migration.

**Alternatives rejected**:
- Multi-tenant customer organizations (Acme Corp model): rejected for v1 because the academic customer base doesn't operate this way. Adds complexity without proportional value.
- Pure individual accounts with no institutional metadata: rejected because reporting and analytics benefit from knowing institutional context.

**Consequences**:
- Customer-side UI shows the requester's own tickets plus any explicitly shared. No "all of my institution's tickets" view.
- If a customer leaves their institution, their personal ticket history remains theirs.
- Future evolution to institution-scoped permissions is possible without breaking schema.

**Deferred**: Multi-user customer organization model (institutional ticket visibility) deferred to potential v2.

---

## DD-012: Slack integration — snapshot capture only, no ongoing bidirectional sync

**Decision**: Slack integration supports creating tickets from thread (emoji-based) and linking threads to existing tickets (slash command). Capture is a snapshot at the moment of linking. No ongoing bidirectional sync of thread messages to ticket comments.

**Rationale**:
- Snapshot capture is well-bounded and tractable to implement correctly.
- Ongoing bidirectional sync has well-known complications: loop prevention, edit/delete handling, attachment differences, identity mapping over time. The complexity is high; the value is incremental over snapshot capture.
- The engineering team has limited experience with chat-centric workflows. Scoping the integration to known-tractable patterns matches team capability.

**Alternatives rejected**:
- Full bidirectional thread/ticket sync: rejected as out of scope for v1.
- No Slack integration at all: rejected because there is genuine value in capturing community-channel discussions into tracked tickets.
- Auto-creation of tickets from chat without explicit user action: rejected because it removes human judgment about what should be tracked vs ephemeral.

**Consequences**:
- Threads continuing after linking accumulate context not in the ticket. Agents can re-link or manually summarize.
- Per-ticket opt-in for ongoing sync remains a possible v2 feature.

**Deferred**: Per-ticket bidirectional sync (Pattern 3 from conversation); per-customer private channels with separate permission classification.

---

## DD-013: Tickets created from public Slack threads default to requester-private

**Decision**: Even though the originating Slack thread was visible to all customers in the public community channel, the resulting ticket defaults to visible only to the requester and support staff. An explicit action ("make community-visible") promotes a ticket to community visibility, typically after resolution.

**Rationale**:
- Tickets often accumulate private information after creation (logs, system configs, account details) that the customer did not intend to put in a public channel.
- Default-private protects against accidental information disclosure.
- Explicit promotion to community-visible enables the community-knowledge value (other customers seeing similar issues benefit from resolved tickets) without making it the default.

**Alternatives rejected**:
- Tickets from public threads default to community-visible: rejected because of accidental private-information risk.
- All tickets community-visible: rejected for obvious privacy reasons.
- No community-visible tickets: rejected because it eliminates the community-knowledge value.

**Consequences**:
- The "community-visible" flag on tickets is a first-class field with its own state management.
- The UI must surface the current visibility clearly to all participants.
- Promotion to community-visible should require explicit confirmation, not be an undo-able default.

**Deferred**: Specific UI affordances for visibility management.

---

## DD-014: Migration approach — big bang cutover with read-only archive

**Decision**: Single cutover date. All teams migrate together. Original Atlassian instance becomes read-only archive.

**Rationale**:
- Parallel operation across two systems for an extended period is itself a substantial cost: training, dual-entry, drift between systems, ambiguity about source of truth.
- Big bang forces decisions: by cutover date, what's curated has been curated, what hasn't goes to archive.
- Read-only archive preserves historical access without ongoing operational burden on the source system.

**Alternatives rejected**:
- Team-by-team phased rollout: rejected because of the dual-system overhead and ambiguity it introduces.
- Permanent parallel operation: rejected as not eliminating Atlassian costs.

**Consequences**:
- Pre-cutover validation gates must be clearly defined and met before cutover commits.
- Curation phase must be time-boxed with a hard deadline; non-curated content goes to archive.
- Rollback plan is limited (you cannot easily un-cut-over). This is a real risk and must be managed via thorough pre-cutover validation.
- Archive must remain accessible (read-only Atlassian instance or static HTML export).

**Deferred**:
- Specific pre-cutover validation gates (architect to define).
- Specific curation criteria (head of engineering to ratify).
- Archive form (kept on reduced license vs HTML export).

---

## DD-015: Custom build scope — three substantive pieces plus aggregation layer

**Decision**: The custom build comprises:

1. **Knowledge management UI** with WYSIWYG markdown editing, page templates, draw.io integration, meeting notes templates, tag/action support, task lists, page-level permissions, user/summary macros. Built as a custom frontend on top of GitLab repos.

2. **External customer service desk portal** with customer login, ticket submission, status views, threaded replies, attachments, integrated knowledge base search. Custom frontend with custom backend logic for ticket permission model.

3. **Cross-project portfolio and risk aggregation views** with scraper-based indexing, filtered views by scope/owner/severity/etc. Internal-only UIs built on admin framework (Refine or similar) for speed.

Plus the foundational pieces: API gateway, permission engine, indexer infrastructure, Slack integration, email integration, schemas, migration pipeline, observability.

**Rationale**: These are the gaps GitLab Ultimate does not fill. Building only these (rather than full Atlassian replacements) keeps scope tractable.

**Consequences**:
- The knowledge management UI is the largest single piece in absolute work terms (WYSIWYG editor integration, page hierarchy, search, permissions).
- The external portal is the highest-stakes piece (paying customers, polished UX expected).
- The aggregation layer is the smallest piece but provides the strategic value (portfolio visibility, risk register).

**Deferred**: Specific feature breakdowns within each piece; v1 vs v2 cuts within each.

---

## DD-016: WYSIWYG editor — TipTap or equivalent ProseMirror-based, not built from scratch

**Decision**: The WYSIWYG markdown editor is built on TipTap (or equivalent ProseMirror-based library) with markdown round-tripping. Building a markdown editor from scratch is explicitly out of scope.

**Rationale**:
- Markdown editor edge cases (paste from Word, table editing quality, accessibility, image upload, code block syntax highlighting, collaborative cursors, undo/redo across structured operations) consume years of work.
- Mature libraries handle most of this. Customization happens on top.
- TipTap is well-documented, actively maintained, and has a large community. BlockNote and Milkdown are alternatives the architect can evaluate.

**Alternatives rejected**:
- Building an editor from scratch: rejected for the reasons above.
- Markdown-only editor with no WYSIWYG: rejected because non-technical users require WYSIWYG.

**Consequences**:
- Dependency on an external library's continued maintenance.
- Customization is bounded by the library's extensibility model.

**Deferred**: Specific choice among TipTap, BlockNote, Milkdown (architect to evaluate against requirements).

---

## DD-017: Vault scope — service credentials and signing keys, not user-facing auth path

**Decision**: Vault stores service account credentials, database/index credentials, signing keys, encryption keys for application-layer encryption, and PKI for mTLS (optional). User authentication goes through Keycloak; Vault is not in the user-facing auth path.

**Rationale**:
- Separation of concerns: Keycloak is the identity authority; Vault is the secrets store.
- Vault availability hiccups should not affect user-facing authentication. If Vault is down but Keycloak is up, users can still log in.
- Service credentials need rotation and Vault handles this well.

**Alternatives rejected**:
- Vault in the user-facing auth path: rejected because it makes user auth dependent on two systems instead of one.
- Storing credentials in environment variables or config files: rejected because rotation becomes a deploy event rather than a Vault operation.

**Consequences**:
- Service-to-service auth via Vault-issued credentials, rotated regularly.
- Vault unavailability degrades service-to-service operations but not user login.

**Deferred**: Specific Vault path structure and rotation policies (architect decision).

---

## DD-018: Identity propagation via OIDC token exchange

**Decision**: Service-to-service calls preserve user identity via OIDC token exchange (RFC 8693). The gateway exchanges the user's token for a downstream token scoped to the target service (typically GitLab). Result: downstream services see the actual human, not the gateway as proxy.

**Rationale**:
- Audit trail clarity: GitLab logs show real user identities, not "the gateway did X on someone's behalf."
- Accountability is preserved across service boundaries.
- Keycloak supports token exchange natively.

**Alternatives rejected**:
- Service account proxying with user identity in header: rejected because downstream systems can't natively log the user identity correctly.
- No identity propagation (gateway acts as itself): rejected for audit clarity reasons.

**Consequences**:
- Keycloak must be configured for token exchange.
- Each downstream service that needs identity propagation must validate exchanged tokens correctly.

**Deferred**: Specific token exchange configuration in Keycloak (architect to specify).

---

## DD-019: Email transport via O365 Microsoft Graph API

**Decision**: Inbound and outbound email goes through O365 via Microsoft Graph API.

**Rationale**:
- The organization already uses O365 for mail.
- Graph API is modern, JSON-based, well-documented.
- No additional mail server to operate.

**Acknowledged limitation**: The organization does not own the email transport. If O365 is down, inbound email-driven ticket creation fails. The sovereignty story is weaker for email than for other components.

**Alternatives rejected**:
- Self-hosted mail server (Postfix, Mailcow): rejected as adding operational burden without sufficient benefit; the organization is committed to O365 for other reasons.
- IMAP polling instead of Graph: rejected because Graph is the modern, supported, richer interface.

**Consequences**:
- Email integration is dependent on O365 availability and Graph API stability.
- Authentication for Graph (service principal, certificate-based) must be configured and credentials stored in Vault.

**Deferred**: Specific Graph API integration patterns (architect to specify; implementer to use mature libraries).

---

## DD-020: Observability via OpenTelemetry

**Decision**: All services emit OpenTelemetry traces, metrics, and structured logs. Correlated through a standard collector and viewer (e.g., Tempo + Prometheus + Loki, or equivalent).

**Rationale**:
- Industry-standard, vendor-neutral, future-proof.
- The organization has used this pattern in other builds.
- OIDC + gateway + downstream service chain particularly benefits from distributed tracing.

**Alternatives rejected**: Vendor-specific APM (Datadog, etc.): rejected for vendor neutrality.

**Consequences**: All services must be instrumented; this is a cross-cutting concern affecting every component.

**Deferred**: Specific collector and backend stack (architect to choose).

---

## DD-021: Schema versioning required from day one

**Decision**: YAML frontmatter on all resources includes a `schema_version` field from the first commit. Schema evolution policy specifies forward compatibility and migration approach.

**Rationale**: Retrofitting schema versioning is painful (every file needs updating; tools must handle "no version means v0"). Front-loading it is cheap.

**Consequences**:
- Every resource creation must include the schema version.
- Indexer and validator must handle multiple schema versions gracefully.
- Migration tooling for schema changes is required.

**Deferred**: Specific schema evolution policy (analyst to specify; architect to implement).

---

## Open items for analyst phase

The following are surfaced for analyst attention. They are not yet decisions:

- **Domain model**: one resource type with views vs four distinct types (tickets, risks, planning items, docs)
- **Definition of "space"**: how Confluence-style spaces map to repos and groups
- **Severity-level definitions**: precise definition of `critical` for webhook triggering
- **Email threading specifics**: Message-ID handling, In-Reply-To/References, subject-line fallback policy
- **Customer portal minimum feature set**: precise scope for v1
- **Authz engine choice**: SpiceDB vs OpenFGA vs custom (analyst to specify access patterns; architect to choose)
- **Disaster recovery posture**: beyond "GitLab's backup story applies"
- **Performance targets**: latency, throughput, concurrency
- **Pre-cutover validation gates**: what proves the new system is ready for big bang
- **Curation criteria for migration**: what counts as "non-relevant"
- **Compliance regime constraints**: any regulatory requirements on risk register format

---

**End of design decisions document.**
