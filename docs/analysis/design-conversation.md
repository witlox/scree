# Scree — Design Conversation

This document distills the design conversation that produced the SEED. It exists so the analyst (and future readers) can see the reasoning behind decisions without having to reconstruct it. It is not a transcript; it is a structured extraction of the substantive content. Where decisions were made, the rationale is captured. Where alternatives were considered and rejected, the reasoning is preserved.

The document is organized by topic rather than chronologically.

---

## Origin and framing

The conversation started from a frustration: the organization runs the Atlassian stack (Jira, Confluence, Service Desk) and Atlassian is moving these to cloud-only with terms the organization finds extractive in cost and limiting in control. The initial framing was "open source replacement OR roll our own with AI assistance."

The framing was challenged early. "I can build complex systems with AI assistance" was identified as load-bearing reasoning that needed scrutiny. The build cost of a system is roughly 20-30% of its total lifecycle cost; operations, incident response, migration, long-tail feature requests, and bus factor are the rest. AI-assisted coding compounds advantages on the build cost; it compounds less on operational longevity. This challenge shaped the rest of the conversation toward: what is the *minimum* custom build, given existing infrastructure?

## Existing infrastructure and what it provides

The organization has:
- **GitLab Ultimate self-managed**: full feature set including epics, iterations, roadmaps, advanced search (Elasticsearch-backed), compliance frameworks, audit events, service desk (basic, per-project), wiki (insufficient for non-technical users).
- **Keycloak**: identity provider with OIDC token issuance and token exchange support.
- **Vault**: secrets management.
- **O365**: email via Microsoft Graph API.
- **Slack**: chat platform. Internal workspace plus a public community channel shared with external academic customers, who interact with staff and with each other in that channel.

User population:
- 150 internal users (mixed engineers and non-technical staff)
- 2000-3000 external customers (academic researchers, individual users)

The conclusion was that GitLab Ultimate provides much of what was initially framed as "needs to be built." The custom build narrows to three substantive pieces plus a thin aggregation layer:

1. Cross-project portfolio and risk aggregation views (planning data and risks accumulate across repos; GitLab does not aggregate well across projects for portfolio-level views)
2. External customer service desk portal (GitLab's Service Desk is email-driven and per-project; insufficient for 2000-3000 external customers expecting a real portal experience)
3. Knowledge management UI suitable for non-technical staff (GitLab Wiki is workable for engineers, mediocre for non-engineers)

## The "run locally during outages" requirement

This requirement shaped the storage architecture decisively. Git-backed storage was chosen because:
- Local clones provide genuine offline read access
- Git history provides a tamper-evident audit trail by construction
- Standard tooling (`grep`, `awk`, IDEs, language servers) works against the data
- Distributed by nature; backups are clones

The requirement was clarified to mean *graceful degradation*, not full offline operation:
- Read access during outages: yes
- Edit existing content with conflict resolution on reconnect: yes
- Create new tickets/issues during outage: no (requires GitLab)
- External user ticket submission during outage: definitely no (requires gateway, GitLab, and O365)

This honesty about scope is important. The "sovereignty" property is real and meaningful. The "fully disconnected operation" property is not claimed.

## Why not just use GitLab Ultimate alone

The question was pressed: given Ultimate's capabilities, why build a custom layer at all? The answer comes down to three specific gaps:

**Knowledge management UX**: GitLab Wiki lacks WYSIWYG appropriate for non-technical users, page templates, draw.io integration, meeting note templates, tagged action items, task lists with cross-page aggregation, page-level permissions independent of project membership, and the macros that Confluence users rely on. For an engineering audience, Wiki is adequate. For a marketing person or PM, it is a significant downgrade from Confluence.

**External customer service desk**: GitLab Service Desk is "email creates an issue." It is not a customer portal with login, multi-ticket views, branded experience, integrated knowledge base, or status/SLA visibility from the customer's perspective. For 2000-3000 external customers, a real portal is required.

**Cross-project aggregation for portfolio and risk**: GitLab's epics are group-scoped, not portfolio-scoped. Cross-project rollups exist (group-level boards, multi-project epics) but are limited for SAFe-style portfolio planning. Risk management at the org level cuts across projects in ways GitLab does not model natively.

These three gaps justify the custom layer. Everything else GitLab provides is reused.

## Storage model: Git with markdown frontmatter

All primary resources (docs, tickets, risks, planning items) are stored as markdown files in GitLab repositories. YAML frontmatter holds structured metadata; the markdown body holds human-readable content.

The pattern matches the user's existing systems (Kiseki, others) and is well-trodden: Git is the source of truth, derived indexes (search, aggregation views) are rebuildable from Git.

The trade-offs were named explicitly:
- *Pro*: sovereignty, audit trail, operability with standard tools, partial offline access
- *Con*: querying structured data against Git is slow without an index; merging conflicts on structured fields requires care; permission model must be layered on top because Git's native permissions are coarse

## Risk register placement

Project-level risks live in the project repo at `risks/`. They inherit permissions from the project. Lifecycle is bounded by the project.

Org-level risks (portfolio, ART, strategic, security, compliance) live in dedicated repos with their own permission boundaries:
- `org/risk-portfolio/`
- `org/risk-security/` (restricted)
- `org/risk-compliance/` (auditor-readable)

The principle: risk lives where the work happens, except when the audience for the risk is broader than the work. The split is pragmatic and inherits naturally from GitLab's group/project permission model.

Escalation is explicit: when a project-level risk needs org visibility, a corresponding risk is created in the appropriate org-level repo, with cross-references back. The duplication is a feature — it forces an explicit "this matters at org level" decision rather than ambient escalation through metadata.

A cross-project aggregation view (the "scraper") walks accessible repos, indexes risks, and provides filtered views. The scraper does not duplicate the permission model — it queries GitLab for authority on every result. The index is a performance optimization; permissions stay authoritative in GitLab.

## Trigger model for indexing

The pattern, applied uniformly to all aggregation indexers:

1. **Hourly batch** as the default. Runs without intervention. Picks up all changes within the hour.
2. **Manual trigger** available to authenticated users. Eliminates "I just updated this, why isn't it showing up" friction.
3. **CRITICAL severity webhook-driven update** for resources tagged appropriately. Webhooks fire only on critical-severity changes; everything else rides the batch.

This pattern is correct because it inverts the cost/benefit of webhooks. Webhooks are expensive operationally (debugging missed deliveries, retry logic, dead-letter queues) but cheap in latency. Batch is the opposite. Paying webhook complexity *only* for the cases where latency genuinely matters (critical risks needing leadership visibility in minutes) is the right trade.

Degradation paths are explicit: webhook fails → batch catches it; batch fails → manual trigger works; all three would need to fail simultaneously for an indexing outage.

## Permission model

Permissions are layered:

**Coarse-grained**: GitLab group and project membership, mapped from Keycloak groups via OIDC claims. This covers most cases: who can read which repos, who can write where, which teams own what.

**Fine-grained for service desk tickets**: ticket-level relations (requester, watcher, assignee) enforced by the API gateway. Relationship-based access control is the natural model. Implementation candidates: SpiceDB, OpenFGA, or a small custom solution.

**Single enforcement point**: all access goes through the API gateway. The gateway is the only path; frontend, CLI, and Slack integration all call the same API. No bypass paths.

**Defense in depth for aggregation views**: aggregation queries hit the derived index for performance, then filter results by the requester's authority over each individual item before returning. The invariant: a user never sees aggregated data that includes items they could not see directly. This invariant is treated as load-bearing and must be explicitly tested.

**Audit**: every gateway action logged with user identity (resolved through Keycloak), resource, action, result. Audit logs are tamper-evident through Git's own history mechanism where possible, supplemented with append-only application logs.

## Identity integration

Keycloak is authoritative. Internal users authenticate via Keycloak; external customers authenticate via Keycloak (likely a separate realm or a `user_type` claim). GitLab consumes Keycloak via OIDC. The gateway consumes Keycloak via OIDC.

Service-to-service identity propagation uses token exchange (RFC 8693). The gateway calls GitLab API on behalf of an authenticated user, exchanging the user's token for a downstream token scoped to GitLab. Result: GitLab's audit logs show the actual human who triggered an action, not "the gateway did it on behalf of someone."

Slack-user-to-Keycloak-user mapping is required for Slack-initiated actions to carry user identity. Email matching is the usual mechanism; SCIM provisioning if available. When mapping fails, the action is refused rather than proceeding with degraded attribution.

## Vault's role

Vault holds:
- Service account credentials (gateway → GitLab API)
- Database/index credentials
- Signing keys for any tokens minted by the gateway
- Encryption keys for application-layer encryption of sensitive fields
- PKI for mTLS between services (optional)

Vault is *not* in the user-facing request hot path. User authentication goes through Keycloak; Vault hiccups should not affect user-facing auth.

## Email integration

O365 via Microsoft Graph API for both inbound and outbound. A small service handles:
- Polling/webhook for inbound mail to the support address
- Parsing inbound mail (MIME, threading via Message-ID and In-Reply-To, attachment handling)
- Creating or updating tickets via the API
- Sending outbound notifications via Graph API with proper threading headers

This is acknowledged as a known-hard problem area for homegrown ticketing. Email parsing has well-known edge cases (HTML emails, signature stripping, encoding nightmares, threading edge cases). The architect should specify the protocols precisely; the implementer should use mature libraries rather than rolling parsers.

A noted limitation: O365 is the email transport, and the organization does not own it. If O365 is down, inbound email-driven ticket creation stops. The sovereignty story is weaker for email than for everything else. This is accepted consciously.

## Slack integration

The Slack space includes a public channel where external academic customers interact with staff and with each other. This is community-with-support, not pure support. The community character has value (customers helping customers, low-friction capture, signal about product issues) that should be preserved.

Integration patterns adopted for v1:

**Outbound notifications**: system events post to Slack channels. Risk escalation to critical → leadership channel. Ticket assignment → DM. Standard pattern.

**Inbound ticket creation from chat**: emoji-based (e.g., `:ticket:` reaction) on a message creates a draft ticket from the thread, with snapshot capture of thread content. Bot acknowledges in thread.

**Inbound ticket linking from chat**: slash command (e.g., `/link-ticket NNN`) attaches the current thread as context to an existing ticket. Permission-respecting autocomplete: only tickets the user can see are offered or accepted.

**Identity preservation**: actions taken via Slack are attributed to the resolved Keycloak user, not the bot. Audit log records Slack origin plus resolved identity.

**No ongoing bidirectional sync**: snapshot capture only. Threads continue in Slack; tickets continue in the system; the moment of linking captures the bridge. Per-ticket opt-in for ongoing sync is deferred to a future version.

**Tickets created from public threads default to requester-private**: even though the originating thread was public, the ticket itself defaults to private to protect against private information being added to the ticket later. An explicit action makes a ticket community-visible.

**Cultural rule, not technical control, for staff posting in public channels**: staff in the public customer channel post as if everything is permanent and public (which it is). The bot does not filter staff vs customer messages when capturing — the rule is that staff should not say private things in public channels in the first place.

Per-customer private channels do not currently exist and are deferred. If they appear later, the bot can be configured per-channel with default visibility classification. The architecture does not preclude this.

The engineering team's limited experience with chat-centric workflows was named. The integration scope is deliberately narrow to match team capability. Resist scope expansion.

## Migration

Decision: big bang cutover. Migrate fully, archive the original as read-only.

Curation is named as the time-consuming phase: every team must review their content and decide what migrates. This phase is non-technical effort that does not scale with engineering team size. Recommended approach: time-box curation to a hard deadline; anything not explicitly curated by the deadline goes to read-only archive.

Migration pipeline scope:
- Jira → tickets in the new system
- Confluence → docs in the new system
- Atlassian Service Desk → tickets in the new system

Non-relevant content is dropped (per curation). Original Atlassian instance becomes read-only archive (either kept on a reduced license tier indefinitely, or exported to static HTML and the instance decommissioned).

## Build organization

**Monorepo** for the custom layer. Reasoning:
- Shared schemas between API, web frontend, CLI — single source of truth for the data model
- Atomic cross-layer changes (add field to schema, update API, update frontend in one MR)
- Single CI and deploy pipeline
- All operators see all code — supports team-build and bus factor

Structure (illustrative; the architect will refine):
```
scree/
├── api/                    # Backend gateway
├── web/                    # Frontend (multi-section single app)
├── cli/                    # CLI client
├── slack-integration/      # Slack bot service
├── email-integration/      # O365 email gateway
├── indexer/                # Aggregation indexers
├── schemas/                # Frontmatter schemas, validation
├── migrations/             # Atlassian → Scree pipelines
├── deploy/                 # IaC, Helm, compose
└── docs/                   # System's own documentation
```

The Slack and email integration services call the main API like any other client. They do not have privileged backend access. This prevents accidental permission bypass via integration paths.

## Frontend approach

Hybrid:
- Custom build for the two user-facing experiences that matter most: knowledge management UI (because non-technical internal users) and external customer portal (because paying customers).
- Admin-framework-based (Refine.dev or similar) for internal-only screens: agent ticket queues, planning dashboards, risk register views, admin tooling.

WYSIWYG markdown editor: TipTap or similar ProseMirror-based solution. Do not build a markdown editor from scratch. The architect should evaluate options against requirements (collaboration, table editing quality, paste-from-Word, accessibility, draw.io integration).

## Update model

Direct commit to main is the default for most resources (tickets updated by agents, doc edits, risk updates by owners). Merge-request-required is configured for an explicit small set:
- Compliance-tagged resources
- Closed risks (preventing silent revision of history)
- Doc paths designated for formal review (e.g., HR policy, security policies)

Enforcement: CODEOWNERS plus branch protection plus push rules. This is a small configuration burden with significant audit benefit for the paths where review matters.

## What was considered and rejected

**Building Confluence/Jira replacements from scratch without leveraging GitLab Ultimate**: rejected because Ultimate provides much of the substrate for free. Custom build was scoped to gaps Ultimate genuinely does not fill.

**Full bidirectional Slack thread sync with tickets** (Pattern 3 from the conversation): considered and explicitly rejected for v1. The complexity is high (loop prevention, edit/delete handling, identity mapping across edits, attachment differences) and the value is incremental over snapshot capture.

**Per-customer private Slack channels with customer-org permission model**: considered (Option 4 from the conversation). Deferred. Architecture should not preclude it; v1 does not implement it.

**Multi-user customer organizations (Acme Corp has 5 users who all see Acme's tickets)**: considered and rejected for v1. Customers are individuals with an org tag for reporting purposes. The org tag is metadata, not a permission boundary, in v1.

**Webhook-driven indexing for all changes**: considered and rejected in favor of the hybrid model (batch + manual + critical-only webhook). Webhooks are operationally expensive; full webhook coverage is over-engineering for non-critical changes.

**Single global risk graph with relationship modeling**: considered. Deferred. The pragmatic split (project risks in project repos, org risks in dedicated repos) is sufficient for the organization's scale. The graph model can emerge later if needed.

**Building a markdown editor from scratch**: explicitly rejected. The edge cases (paste from Word, table editing, accessibility, collaborative cursors) consume years of work. TipTap or equivalent is mandatory.

## Open items that were named but not resolved

These are surfaced in the SEED's "Initial Hard Questions" section and `open-questions.md` for the analyst phase:

- Domain model: one resource type with views vs four distinct types
- Definition of "space" in the system
- Frontmatter schema versioning and migration
- Precise definition of `severity: critical` for the webhook trigger
- Specific email threading approach (Message-ID handling, fallbacks)
- Minimum feature set for the external customer portal v1
- Choice of authz engine
- Choice of markdown editor (architect decision after analyst specifies requirements)
- Disaster recovery posture beyond "GitLab's backup story applies"
- Performance targets (analyst to specify the need; architect to specify the numbers)
- Pre-cutover validation gates for big bang migration
- Curation criteria for "non-relevant" content
- Compliance regime constraints on risk register format (if any) — needs head of engineering input

---

**End of design conversation document.**
