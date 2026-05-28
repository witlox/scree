# Scree — Analyst Seed

**Working title**: Scree
**Tagline**: Git-native knowledge, planning, and service desk for an org leaving Atlassian
**Status**: Seed — pre-analyst
**Naming rationale**: A scree is a slope of accumulated rock fragments at the base of a cliff. The metaphor is that organizational knowledge, tickets, plans, and risks accumulate as a pile of artifacts that has shape and structure if you read it right. The system makes the pile navigable without pretending it's anything other than a pile.

---

## 1. Problem

The organization currently runs Atlassian's stack — Jira (project planning with SAFe-flavored agile), Confluence (static docs, meeting notes, design docs), and Service Desk (external customer support, internal team handoffs). Atlassian is moving these to cloud-only with licensing terms the organization considers extractive. The organization has GitLab Ultimate self-managed, Keycloak for identity, Vault for secrets, O365 for mail, and Slack for ephemeral discussion (including a public community channel where external academic customers interact with staff and with each other).

The organization wants to replace the Atlassian stack with a system that:

- Runs entirely on infrastructure the organization controls
- Stores its primary data as markdown files in Git repositories (sovereignty, operability, audit trail, partial offline access)
- Integrates cleanly with existing Keycloak, Vault, GitLab, O365, and Slack
- Reuses what GitLab Ultimate already provides rather than rebuilding it
- Adds the layers GitLab does not provide well: cross-project portfolio and risk aggregation, an external customer service desk portal, and a knowledge management UI suitable for non-technical staff

No service currently in the stack is authoritative about cross-project planning, organizational risk, customer support tickets, or organizational knowledge. This is the gap Scree fills.

## 2. Primary Questions for the Analyst

The architect and adversary will need answers to these before producing interfaces. The analyst's job is to formalize them as specifications, ubiquitous language, invariants, and failure modes.

1. **What is the ubiquitous language across docs, tickets, planning items, and risks?** These four resource types share concepts (owner, status, history, references) but each has its own native vocabulary. The analyst must produce a single coherent vocabulary or justify why distinct vocabularies are unavoidable.

2. **What is the authoritative permission model and where is it enforced?** Multiple identity surfaces (Keycloak as IdP, GitLab as repo authority, Slack as channel-scoped) must compose into a single answer to "can principal P perform action A on resource R?" without introducing leak paths.

3. **What invariants govern resource lifecycle?** Tickets, risks, and planning items have state machines. Docs do not (they have versions, not states). What state transitions are legal, who can perform them, and what evidence must be captured?

4. **What is the failure mode catalog?** Concrete enumeration of how the system can fail: GitLab unreachable, O365 unreachable, Slack webhook missed, Keycloak token expired mid-operation, scraper missed a CRITICAL risk, permission cache stale, etc. Each with severity and proposed mitigation.

5. **What is the schema for resource frontmatter, and how does it evolve?** All resources are markdown files with YAML frontmatter. Schema versioning, validation, migration on schema change — these need a coherent story before any code is written.

6. **What are the cross-resource references and their integrity constraints?** Risks reference tickets, tickets reference docs, planning items reference epics, Slack threads link to tickets. What happens when a referenced resource is deleted, moved, or its permissions change?

7. **What does "partial offline operation" mean concretely?** Reads from local clones during GitLab outage: yes. Writes queued for replay: undefined. Ticket creation: no. The analyst must produce a precise specification of what works offline, what degrades gracefully, and what fails outright — including for each user role (internal, external, agent, operator).

## 3. Constraints

These are decisions already made in conversation with the head of engineering. They are not negotiable in the analyst phase but the analyst may flag them for revisit if they conflict with discovered invariants.

### Technical constraints
- **GitLab Ultimate self-managed** is the primary substrate. Scree augments GitLab; it does not replace what GitLab already does well.
- **Keycloak** is the identity provider. OIDC tokens are the auth currency for all user-facing operations. Token exchange (RFC 8693) is the mechanism for service-to-service identity propagation.
- **Vault** holds service credentials and signing keys. It is not in the user-facing request hot path.
- **O365 via Microsoft Graph API** is the email transport. The organization does not own inbound mail; this is an accepted dependency.
- **Slack** is the chat platform. One public channel hosts community interaction between external academic customers and staff. No Slack Connect with customers, no per-customer private channels (deferred).
- **All primary data is markdown with YAML frontmatter** in Git repositories. Derived indexes (search, aggregation) are rebuildable from Git.
- **Permissions are inherited from GitLab repo/group structure** for coarse-grained zones, augmented by an application-layer policy engine for resources that need finer-grained rules (specifically: external service desk tickets with requester/watcher/assignee relations).
- **Attachments**: Git LFS for internal docs and risks where the "clone and have everything" property matters; S3-compatible object storage for external service desk attachments where the access pattern is different.

### Architectural constraints
- **Monorepo** for the custom layer: API gateway, web frontend, CLI, schemas, deployment, migration tooling all in one repository.
- **API-first**: every operation exposed via the same API used by web frontend, CLI, Slack integration, and any future automation.
- **Single permission enforcement point**: all access goes through the API gateway's authz module. No bypass paths.
- **Custom WYSIWYG editor on top of markdown**: TipTap or equivalent ProseMirror-based editor. Output is clean markdown round-tripped through Git.
- **OpenTelemetry** for observability across all services.

### Workflow constraints
- **Update model is mostly direct commit**, with merge-request-required paths for an explicit small set: compliance-tagged resources, closed risks, and any doc paths designated for formal review. Enforced via CODEOWNERS plus branch protection.
- **Trigger model for indexing**: hourly batch as the default, manual trigger available, webhook-driven update only for resources tagged `severity: critical`.

## 4. Non-Goals (v1)

These are explicitly out of scope for the initial build. The analyst should resist pulling them back in. They are listed so the boundary is explicit.

- **Replacement for any GitLab-native feature that works adequately**: code review, CI/CD, repo permissions, MR workflows, group/project hierarchy, the existing GitLab issues and epics for engineering work.
- **Replacement of GitLab's existing planning primitives where they suffice**: team-level epics, iterations, milestones, issue boards. Scree's planning layer aggregates and supplements these for portfolio and ART-level views; it does not duplicate them.
- **A separate identity store**: Keycloak is authoritative. Scree does not maintain its own user database beyond mapping tables for non-OIDC integrations.
- **Full bidirectional Slack thread sync with tickets**: snapshot capture on linking only. Per-ticket ongoing sync is deferred.
- **Per-customer private Slack channels with their own permission model**: deferred. The current public community channel is the only Slack surface.
- **Slack Connect with customer organizations**: deferred.
- **Multi-tenant customer organization model**: customers are individuals tagged with an organizational affiliation (metadata, not a permission boundary). Tickets are individually owned; the owner can explicitly share with named users. Institution-wide ticket visibility is not v1.
- **Federated identity for external customers beyond Keycloak's native external-realm capabilities**: customer institutional SSO federation is not v1.
- **Internationalization**: English only in v1. Schema and architecture should not preclude i18n later, but no translation infrastructure is built.
- **Fully disconnected operation with conflict-resolved replay**: offline reads from local clones work; ticket and risk creation while disconnected does not. This is documented as graceful degradation, not full HA.
- **Migration from non-Atlassian sources**: the migration pipeline is Atlassian-specific. Generic ingestion is out of scope.
- **Mobile-native applications**: web UI must be responsive; native apps are not built.
- **Customer-to-customer direct messaging through Scree**: the existing Slack space serves this purpose. Scree's portal is for ticket interaction.

## 5. Stakeholders

- **Head of engineering**: executive sponsor. Decides scope cuts. Owns vendor exit timeline.
- **Internal users (~150)**: all internal staff. Mix of engineers and non-technical roles (researchers, support staff, administration). Daily users of docs and planning; some are agents on the service desk.
- **External customers (~2000–3000)**: academic researchers. Individual users. Submit tickets via email, web portal, or community Slack channel. Some are active community members helping other customers.
- **Build team**: shared ownership across multiple engineers, building together with the same workflow. Bus factor managed by collective ownership rather than individual heroics.
- **Compliance / audit (if applicable)**: not explicitly named in conversation but implied for risk register and audit trail features. Analyst should flag this as a stakeholder to confirm with the head of engineering.
- **Operations / SRE**: operators of the deployed system. Need observability, runbooks, and incident-response capability. May overlap with build team.

## 6. Prior Art

The analyst should review these for borrowed patterns, anti-patterns, and unresolved problems:

### Direct prior art
- **GitLab Ultimate self-managed**: the substrate. Particularly: Service Desk (per-project email-driven ticket creation), Advanced Search (Elasticsearch-backed), Epics and Roadmaps, Compliance Frameworks, Wiki (insufficient for non-technical users — informs why Scree exists). The analyst should produce a feature-by-feature gap analysis between Ultimate's capabilities and what Scree adds.

### Chat-integrated work tracking
- **Linear's Slack integration**: reference implementation for emoji-based ticket creation and slash-command linking. Their model of opt-in per-ticket sync (rather than default-everything-sync) informs Scree's snapshot-only default.
- **Plain.com**: chat-first support model with structured ticket layer. Useful for the community-vs-tracked tension.
- **Height**: another reference for ticket capture from chat without overreaching.

### Git-as-database systems
- **Sourcehut**: email-driven, Git-native development platform. Different domain but informs the "Git is truth, gateway adds web UI" pattern.
- **Radicle**: peer-to-peer code collaboration with Git-native issues and patches. Informs the offline-capable read model.
- **Gitea, Forgejo**: lightweight Git forges. Mostly relevant for what they choose not to build (in contrast to GitLab Ultimate).

### Authorization
- **Google Zanzibar**, **SpiceDB**, **OpenFGA**: relationship-based access control implementations. The service desk ticket model (requester, watcher, assignee, owner) maps naturally to ReBAC. The analyst should determine whether Scree needs ReBAC or whether GitLab's RBAC plus a small custom layer suffices.

### Markdown editing
- **TipTap**, **BlockNote**, **Milkdown**: ProseMirror-based editors with markdown round-tripping. The analyst should evaluate which to standardize on, considering: collaboration features needed, table editing quality, paste-from-Word behavior, accessibility.

### Migration prior art
- The analyst should flag that migration from Jira and Confluence is its own substantial workstream with its own prior art (Atlassian's REST APIs, various third-party export tools). Migration is in scope for v1 but is a separable concern from the core system design.

## 7. Initial Hard Questions

These are the questions the analyst → architect → adversary chain must work through. The seed does not answer them; it surfaces them.

### Domain modeling
1. Are tickets, risks, planning items, and docs four resource types or four views of one resource type? Argument for one type: they share metadata patterns (owner, references, history, permissions). Argument for four: their state machines and lifecycles are genuinely different. The analyst should produce a domain model that takes a position.

2. What is a "space" in Scree? Confluence has spaces. Repos have namespaces. Slack has channels. The analyst must define the unit of organization and its relationship to GitLab groups and projects.

3. How does the "org tag" on external customer accounts work? Pure metadata for reporting? Or a future-permission-boundary placeholder? The analyst should specify the data model now in a way that doesn't preclude future use as a permission boundary, without committing to that semantic yet.

### Permission boundaries
4. The system has at least these principal types: internal user, external customer, agent, operator, service account, Slack bot acting on behalf of a user. The analyst must enumerate them precisely and specify what each can do where.

5. Permission leakage in aggregation views is the primary security risk. Every cross-project query must filter results by the requester's authority over each individual item. The analyst should specify the invariant precisely and propose how it's tested.

### Lifecycle and state
6. What happens to a risk when the team that owns it is reorganized? When the project containing it is archived? When the owner leaves the organization? The orphan handling answer is "highlight orphaned actives for manual reassignment" — the analyst must specify when this check runs, what counts as orphaned, and what UI/notification surfaces it.

7. Tickets can be created from email, web portal, Slack, or API. Each origin carries different identity, different content fidelity, different attachment semantics. The analyst should specify the unified ticket creation flow and how origin-specific differences are normalized.

### Migration
8. What is the precise cutover plan? Big bang is the decision. The analyst should specify the pre-cutover validation gates (what proves the new system is ready), the cutover-day runbook (in outline; details for the integrator), and the rollback plan (if any — big bang implies limited rollback).

9. What is "non-relevant" content for migration purposes? Time-based cutoff? Per-team curation? The analyst should propose criteria for migration vs archive and surface the question for the head of engineering to ratify.

### External service desk
10. The customer portal is the highest-stakes UI in the system (paying customers, polished expectations). What is its minimal feature set for v1? The analyst should specify a deliberately narrow scope and identify what is deferrable.

11. Email threading reliability is a known failure mode for homegrown ticketing. What is the specific approach (Message-ID handling, In-Reply-To/References, subject-line fallback)? The analyst should make this concrete enough that the architect can specify protocols.

### Risk register
12. The split between project-level risks (in project repo) and org-level risks (in dedicated repos) is decided. The aggregation layer ("scraper") that pulls project-level risks into an org-level view needs precise specification of: trigger conditions, schema validation, conflict handling, permission filtering at query time, and orphan/deletion semantics.

13. Risk severity levels need a precise definition, especially `critical` (which triggers webhook-driven near-real-time indexing). The analyst should propose definitions and flag for stakeholder ratification.

### Slack integration
14. Identity mapping between Slack users and Keycloak users — what is the precise mechanism, and what is the fallback when mapping fails? (Refuse the operation? Proceed with degraded attribution?)

15. The line between "ephemeral community discussion" and "captured tracked work" is a design choice. The analyst should specify the explicit moment of transition (the emoji or slash command), what gets captured, and what does not.

## 8. Out of Scope for Analyst Phase

The following are architect or implementer concerns. The analyst should not attempt to resolve them but may surface them as open questions for downstream phases:

- Specific choice of markdown editor (TipTap vs BlockNote vs others) — architect decision after evaluating against specified requirements.
- Specific choice of authz engine (SpiceDB vs OpenFGA vs custom) — architect decision after analyst has specified the access patterns and invariants.
- Specific frontend framework — architect decision.
- Specific backend language (Rust vs Go) — architect decision, informed by the existing organization's stack expertise.
- Specific deployment topology (k8s vs compose, single binary vs services) — architect and integrator decision.
- Performance targets (latency, throughput) — analyst should flag the need to specify these but the numbers themselves come from the architect after profiling.

## 9. Graduation Criteria

Before the analyst hands off to the architect, the following must exist:

- [ ] `specs/domain-model.md` — entities, relationships, state machines for tickets, risks, planning items, docs
- [ ] `specs/ubiquitous-language.md` — single vocabulary, no synonyms
- [ ] `specs/invariants.md` — testable assertions that must always hold
- [ ] `specs/assumptions.md` — explicit, falsifiable assumptions the design depends on
- [ ] `specs/failure-modes.md` — enumerated failure modes with severity and proposed mitigation
- [ ] `specs/features/*.feature` — Gherkin scenarios for every capability identified above, with concrete values
- [ ] `specs/cross-context/interactions.md` — which subsystems talk to which, and how
- [ ] `specs/permission-model.md` — principals, resources, actions, and the precise invariants on access
- [ ] `specs/frontmatter-schemas/` — schema definitions for each resource type with versioning story
- [ ] `specs/open-questions.md` — items deferred or escalated to the head of engineering

No TODO or TBD markers remain in any spec file at handoff time.

## 10. Notes for the Analyst

This is a multi-resource system spanning four distinct domain concepts (docs, tickets, risks, planning items) plus integration with at least five external systems (GitLab, Keycloak, Vault, O365, Slack). The temptation will be to model each resource type independently and discover the cross-cutting concerns later. Resist this. The cross-cutting concerns — permissions, schema, references, audit, history — are the system. The resource-type-specific concerns are skin.

The user has explicitly noted: "decompose before deciding" and "trade-offs are fundamental." When two requirements conflict, name the conflict explicitly in `open-questions.md` and escalate rather than resolving on instinct. The user prefers explicit deferral to assumed resolution.

The user has also noted concern about permission leakage in aggregation views. Treat the permission invariant as load-bearing. The analyst's invariants document should include the precise statement of the access-control property and propose how it's tested.

The user's organization has limited experience with chat-centric workflows. The Slack integration scope is deliberately narrow. Resist the temptation to grow it. If a feature seems to need richer Slack integration, flag it for revisit rather than expanding scope.

---

**Begin analyst phase.**
