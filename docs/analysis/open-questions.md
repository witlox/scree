# Scree — Open Questions

This document enumerates questions that remain open at the end of the design conversation. They are grouped by who should resolve them: analyst (during analyst phase), architect (after analyst hands off), head of engineering (stakeholder ratification), or deferred (post-v1).

The analyst should add to this document as new questions surface during specification work. The pattern is: every new question gets logged, with the proposed owner, even if it gets resolved quickly. This produces a traceable record of what was uncertain and how it was resolved.

---

## Analyst-phase questions

These should be resolved in the analyst phase, producing specifications, invariants, or further design decisions.

### Domain modeling

**OQ-A-001**: Are tickets, risks, planning items, and docs four distinct resource types, or four views of a unified resource type?

*Considerations*: They share metadata patterns (owner, references, history, permissions). They differ in state machines and lifecycles. A unified type with subtypes is more elegant but requires careful handling of subtype-specific behavior. Distinct types are more straightforward but produce more code duplication.

*Owner*: Analyst.

**OQ-A-002**: What is a "space" in Scree, and how does it relate to GitLab groups, projects, and Slack channels?

*Considerations*: Confluence's "space" is a high-level grouping for related content. Mapping naively to GitLab projects works for some cases (per-team docs) but not others (cross-team documentation, public knowledge base). The analyst should propose a coherent model.

*Owner*: Analyst.

**OQ-A-003**: How does the "org tag" on external customer accounts evolve over time?

*Decision in v1*: pure metadata for reporting. *Future option*: could become a permission boundary for institutional visibility. The analyst should specify the data model now in a way that doesn't preclude future evolution, without committing to the semantic yet.

*Owner*: Analyst.

**OQ-A-004**: What are the precise principal types in the system, and what can each do where?

*Initial list*: internal user (with sub-roles), external customer, agent, operator, service account, Slack bot acting on behalf of a user. The analyst must enumerate precisely and specify access patterns for each.

*Owner*: Analyst.

### Lifecycle and state

**OQ-A-005**: When is an "active" resource considered orphaned?

*Decision*: orphaned actives are highlighted for manual reassignment. The analyst must specify: when the orphan check runs, what counts as orphaned (owner left org? owner inactive for N days? owner deleted entirely?), how the orphan is surfaced (UI? notification? batch report?), what reassignment workflow exists.

*Owner*: Analyst.

**OQ-A-006**: What are the precise state machines for tickets, risks, and planning items?

*Considerations*: States, allowed transitions, who can perform transitions, what evidence is required. The analyst should specify state machines as testable invariants.

*Owner*: Analyst.

**OQ-A-007**: How are ticket origins (email, web, Slack, API) normalized into a unified ticket creation flow?

*Considerations*: Each origin carries different identity fidelity, content format, attachment semantics. The analyst must specify the normalization and what is preserved as origin-specific metadata.

*Owner*: Analyst.

### Schema and references

**OQ-A-008**: What is the frontmatter schema for each resource type, and how does the schema evolve?

*Considerations*: Versioning approach (`schema_version` field — decided), validation strategy, migration on schema change, backward compatibility window. The analyst must produce the v1 schemas and the evolution policy.

*Owner*: Analyst.

**OQ-A-009**: What are the integrity constraints on cross-resource references?

*Considerations*: Risks reference tickets, tickets reference docs, planning items reference epics, Slack threads link to tickets. What happens when a referenced resource is deleted? Moved? Has its permissions changed such that the referencing user can no longer see it?

*Owner*: Analyst.

### Permission invariants

**OQ-A-010**: What is the precise statement of the aggregation view permission invariant, and how is it tested?

*Considerations*: The invariant: "a user accessing an aggregation view never sees data they could not see by accessing the source directly." The analyst must specify this precisely and propose a testing strategy. This is load-bearing — must not be vague.

*Owner*: Analyst.

**OQ-A-011**: How are permission changes propagated to caches?

*Considerations*: TTL strategy, explicit invalidation events, defense-in-depth against stale cache leaks. The analyst should specify the constraints; the architect implements.

*Owner*: Analyst.

### Failure modes

**OQ-A-012**: Enumerate the failure modes and their severities.

*Initial list*: GitLab unreachable, O365 unreachable, Slack webhook missed, Keycloak token expired mid-operation, scraper missed a CRITICAL risk, permission cache stale, Vault unreachable, indexer crashed mid-batch, email parsing failure, attachment storage failure, etc. Each needs severity (SEV-1 through SEV-3 or similar) and proposed mitigation.

*Owner*: Analyst.

### Severity definitions

**OQ-A-013**: Define `severity: critical` precisely.

*Considerations*: This field drives webhook-triggered immediate indexing. If everything is critical, nothing is. Need concrete definition with examples. Proposed scope from conversation: "imminent threat to delivery, safety, security, or compliance requiring immediate cross-team awareness."

*Owner*: Analyst (proposal) + Head of Engineering (ratification).

### Email integration specifics

**OQ-A-014**: Specify email threading approach in detail.

*Considerations*: Message-ID handling, In-Reply-To and References header policy, subject-line fallback when headers are missing, HTML vs plain text handling, signature stripping, attachment handling, encoding edge cases.

*Owner*: Analyst (specification) + Architect (protocol details).

### External customer portal scope

**OQ-A-015**: Define the minimum feature set for the external customer portal v1.

*Considerations*: Login, submit ticket, view own tickets, reply, attach files, see status. What else? Search across own tickets? Search across community-visible tickets? Knowledge base integration? Profile management? Subscription preferences?

The analyst should propose a deliberately narrow scope and explicitly identify deferrable features.

*Owner*: Analyst (proposal) + Head of Engineering (ratification).

### Slack integration specifics

**OQ-A-016**: Specify Slack-user-to-Keycloak-user identity mapping.

*Considerations*: Mechanism (email match, SCIM, manual mapping), fallback when mapping fails (refuse operation vs. proceed with degraded attribution — current decision: refuse), maintenance (what happens when a user changes their email).

*Owner*: Analyst.

**OQ-A-017**: Specify the exact emoji/command pattern for ticket creation and linking.

*Considerations*: Which emoji? Which command? What is the autocomplete behavior? What is the visual feedback in the thread?

*Owner*: Analyst (propose) + Architect (implement).

### Risk register schema

**OQ-A-018**: Specify the risk register frontmatter schema in detail.

*Initial fields from conversation*: id, title, likelihood, impact, score, strategy (ROAM or Avoid/Transfer/Mitigate/Accept), owner, accountable, review_by, affects (scope), mitigations (links), triggers, related_risks, schema_version, severity.

*Owner*: Analyst.

### Pre-cutover validation

**OQ-A-019**: Specify pre-cutover validation gates for big bang migration.

*Considerations*: What proves the new system is ready? Specific test scenarios that must pass? Load testing thresholds? User acceptance criteria? Migration data validation (X% of records migrated correctly)?

*Owner*: Analyst (specification) + Head of Engineering (ratification of "ready").

### Curation criteria

**OQ-A-020**: Specify curation criteria for "non-relevant" content during migration.

*Considerations*: Time-based cutoff (e.g., older than 2 years)? Explicit per-team decision? Activity-based (no edits in N months)? Combination?

*Owner*: Analyst (proposal) + Head of Engineering (ratification).

---

## Architect-phase questions

These are flagged for the architect but not resolved by the analyst.

### Component selection

**OQ-X-001**: Choose authorization engine: SpiceDB vs OpenFGA vs custom.

*Considerations*: Operational complexity, schema migration story, performance at Scree's scale, community health, integration with existing stack.

*Owner*: Architect (after analyst specifies access patterns).

**OQ-X-002**: Choose WYSIWYG editor: TipTap vs BlockNote vs Milkdown vs others.

*Considerations*: Markdown round-tripping, table editing, paste-from-Word, draw.io integration, collaboration, accessibility.

*Owner*: Architect (after analyst specifies editor requirements).

**OQ-X-003**: Choose backend language. ~~Rust vs Go~~ — **RESOLVED** (2026-05-28) → ADR-0002 (Python + FastAPI). See `resolved-questions.md`.

**OQ-X-004**: Choose frontend framework and admin framework. **RESOLVED** (2026-05-28, framework) → ADR-0003 (React + TS / htmx). Specific admin-framework library remains an architect decision; see `resolved-questions.md`.

**OQ-X-005**: Choose monorepo tooling (Nx, Turborepo, etc.) or none.

*Considerations*: Build performance at expected codebase size, team familiarity, complexity overhead.

*Owner*: Architect.

### Performance targets

**OQ-X-006**: Specify performance targets for user-facing operations.

*Considerations*: Page load times, search response times, ticket creation latency, indexer throughput. The analyst flags the need; the architect specifies numbers based on profiling and user expectations.

*Owner*: Architect.

### Deployment topology

**OQ-X-007**: Specify deployment topology.

*Considerations*: Kubernetes vs Docker Compose, single-binary vs multi-service, HA configuration, deployment automation.

*Owner*: Architect + Integrator.

### Disaster recovery

**OQ-X-008**: Specify disaster recovery posture beyond "GitLab's backup story applies."

*Considerations*: Indexer state recovery (rebuildable from Git, but how fast?), Vault backup, audit log preservation, customer-facing communication during outages.

*Owner*: Architect.

---

## Head of Engineering ratification

These need explicit stakeholder input. The analyst should surface them; the head of engineering makes the call.

**OQ-HE-001**: Ratify `severity: critical` definition.

**OQ-HE-002**: Ratify external customer portal v1 minimum feature set.

**OQ-HE-003**: Ratify pre-cutover validation gates.

**OQ-HE-004**: Ratify migration curation criteria and deadline.

**OQ-HE-005**: Confirm compliance regime constraints (any regulatory requirements on risk register format? Audit trail requirements? Data retention obligations? GDPR data subject request handling?).

**OQ-HE-006**: Confirm budget envelope and rollback constraints.

**OQ-HE-007**: Confirm timing of Atlassian disclosure (kept internal vs disclosed for negotiation leverage).

**OQ-HE-008**: Confirm compliance/audit team as stakeholders. Are they consumers of risk register, audit logs, ticket history? Do their requirements constrain the design?

**OQ-HE-009**: Confirm list of paths requiring MR-based update (compliance-tagged content, closed risks, designated doc paths).

**OQ-HE-010**: Confirm archive strategy: read-only Atlassian instance kept on reduced license vs static HTML export with full decommission.

---

## Deferred to v2 or later

These are explicitly out of scope for v1. Listed so they are not pulled back in during specification work.

**OQ-D-001**: Multi-user customer organization model (Acme Corp has 5 users who all see Acme's tickets).

**OQ-D-002**: Bidirectional Slack thread/ticket sync (Pattern 3 from conversation).

**OQ-D-003**: Per-customer private Slack channels with separate permission classification.

**OQ-D-004**: Slack Connect with customer organizations.

**OQ-D-005**: Federated identity for external customers beyond Keycloak's native external-realm capabilities.

**OQ-D-006**: Internationalization (translation infrastructure).

**OQ-D-007**: Fully disconnected operation with conflict-resolved write replay.

**OQ-D-008**: Migration from non-Atlassian sources (generic ingestion).

**OQ-D-009**: Mobile-native applications.

**OQ-D-010**: Single global risk graph with relationship modeling (beyond per-repo split).

**OQ-D-011**: Per-ticket opt-in bidirectional sync.

**OQ-D-012**: Customer-to-customer direct messaging through Scree (Slack serves this purpose).

---

## Process for adding new open questions

When the analyst (or any subsequent role) encounters a new question:

1. Assign an ID (OQ-A-NNN for analyst-phase, OQ-X-NNN for architect-phase, OQ-HE-NNN for head-of-engineering ratification, OQ-D-NNN for deferred).
2. State the question precisely.
3. List considerations briefly.
4. Identify owner.
5. If resolved, mark it resolved with date and link to the specification or decision document.

Resolved open questions move to a separate `resolved-questions.md` (created when needed) so the active set stays clean.

---

**End of open questions document.**
