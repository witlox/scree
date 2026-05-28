# Scree — Prior Art Evaluation

This document evaluates relevant prior art for the Scree design. The purpose is twofold: surface patterns worth borrowing, and identify pitfalls already discovered by others so the analyst does not re-encounter them in implementation.

The evaluation is organized by problem area rather than by product, because most relevant prior art addresses one or two problems each rather than the whole solution space.

---

## 1. GitLab Ultimate as substrate

GitLab Ultimate self-managed is not "prior art" in the traditional sense — it is the *platform* Scree builds on. Treating it accurately is the most important prior-art evaluation, because it determines what Scree must build versus reuse.

### What GitLab Ultimate already provides

Substantive features Scree should not rebuild:

- **Issues, sub-issues, related issues**: per-project work tracking. Adequate for engineering work; integrates with code (MRs close issues, time tracking, etc.).
- **Epics, sub-epics, multi-level epic hierarchy**: group-scoped grouping of work. The SAFe "feature" layer maps reasonably here.
- **Iterations with cadences**: sprint-equivalent timeboxing.
- **Milestones**: cross-project goals with deadlines.
- **Roadmaps**: epic-timeline visualization.
- **Issue boards, epic boards**: kanban-style views, at project, group, and personal scopes.
- **Issue dependencies, dependency visualization**: blocking relationships explicit and visualized.
- **Advanced Search**: Elasticsearch-backed search across code, issues, MRs, comments, wiki, commits.
- **Wiki**: per-project markdown wiki with version history.
- **Service Desk**: per-project email-driven ticket creation. Issues created from email with proper threading.
- **Compliance Frameworks**: policy enforcement across projects (MR approvals, security scans, etc.).
- **Audit Events**: comprehensive audit log across the platform.
- **Push Rules, Branch Protection, CODEOWNERS**: enforcement mechanisms for who can change what.
- **OIDC Identity Provider integration**: native Keycloak consumption.
- **Group/project permission model**: roles (Guest, Reporter, Developer, Maintainer, Owner) with sane defaults.
- **Container Registry, Package Registry**: storage for build artifacts.
- **CI/CD**: pipelines, runners, secrets management for builds.

### Where GitLab Ultimate is insufficient

The gaps Scree fills:

**Wiki UX for non-technical users**: GitLab Wiki has markdown editing, version history, page hierarchy. It lacks:
- WYSIWYG that feels like a knowledge tool rather than a developer tool
- Page templates and template inheritance
- Macros (dynamic content, embedded queries, page reports)
- Page-level permissions independent of project membership
- Cross-wiki search with consistent UX
- Embedded structured content (decision logs, action items aggregated across pages)
- draw.io / diagrams.net integration
- Comment threads on pages (only on MRs and issues)

For an engineering team, GitLab Wiki is adequate. For a marketing person, PM, or researcher, it is a significant downgrade from Confluence.

**Service Desk for external customers at scale**: GitLab Service Desk creates issues from email. It is not:
- A customer-facing portal with login and ticket views
- A multi-ticket dashboard for customers
- A branded support experience
- An integrated knowledge base linked to ticket creation
- A view of SLA status and history from the customer's perspective
- A multi-customer-organization aware model

For internal team-to-team work, Service Desk is adequate. For 2000-3000 external customers, a real portal is required.

**Cross-project portfolio and risk aggregation**: GitLab provides:
- Group-level epic boards (some cross-project visibility)
- Group-level roadmaps (timeline aggregation)
- Multi-project pipeline views

It does not provide:
- Portfolio-level views above group hierarchy
- Risk register aggregation across projects
- SAFe-style PI commitment tracking with capacity vs load
- Dependency visualization across teams/ARTs
- Strategic theme aggregation

The user has noted these are precisely the layers GitLab handles poorly because audience is leadership/RTEs rather than engineers, and where data volume is small enough that custom build is tractable.

### Patterns to borrow from GitLab

- **Group/project hierarchy as permission model**: well-tested, sane defaults. Scree's permission model leverages this directly.
- **Audit events structure**: comprehensive coverage, consistent format. Scree's audit log should follow similar patterns.
- **OIDC token exchange for service-to-service**: GitLab does this; Scree gateway does the same.
- **CODEOWNERS + branch protection**: enforcement mechanism for review requirements. Scree uses this for compliance-tagged paths.
- **Webhooks for change notifications**: standardized format Scree's integrations can consume.

### Anti-patterns to avoid

- **GitLab Wiki's editor**: the implementation is awkward enough that non-technical users prefer Confluence. Scree's editor must be substantially better.
- **GitLab Service Desk's per-project model**: the per-project scope makes it unsuitable for a unified customer experience. Scree's service desk must be cross-cutting.
- **GitLab Issues as a portfolio planning tool**: it isn't one. Don't pretend.

---

## 2. Chat-integrated work tracking

Several products have addressed the "create tickets from chat" problem. Their solutions inform Scree's Slack integration.

### Linear's Slack integration

Particularly relevant. Linear has solved most of the edge cases:

- `/linear` slash command for creating issues
- Mention pattern (`ENG-123`) that auto-unfurls and offers contextual actions
- "Create from message" via Slack's message action menu (the `...` menu)
- **Thread sync is opt-in per ticket**, not default-on

The opt-in-per-ticket sync model is the right answer. Defaulting to sync everything creates loops, edit-handling problems, attachment ambiguity, and noise. Defaulting to snapshot capture and allowing explicit per-ticket sync activation matches the actual access pattern: most tickets don't need ongoing chat sync; the few that do can have it.

Scree adopts Linear's pattern. Snapshot capture is the v1 default; per-ticket ongoing sync is deferred to v2.

### Plain.com

Chat-first support model. The whole product is built around the premise that customer support starts in chat and structured ticketing is layered on top, not the other way around. Relevant for the community-vs-tracked tension in Scree's external service desk.

Key insight: customers prefer chat for low-friction interaction. Forcing them into a portal increases friction and reduces engagement. Scree's mixed model (Slack community channel + email + portal) reflects this.

### Height, Notion, Coda integrations

Various ticket-from-chat implementations. The common pattern: explicit user action (emoji reaction or slash command) to promote a chat message into a tracked item. Implicit capture (heuristic detection of "this looks like a bug report") universally fails in practice; users do not predict what the heuristic will catch and stop trusting it.

Scree follows this pattern: explicit user action only.

### Anti-patterns from chat integration

- **Auto-creation of tickets from heuristic detection of chat content**: fails reliably. Users stop trusting the system.
- **Full bidirectional thread/ticket sync by default**: creates loops, edit-handling problems, identity confusion. Scree explicitly rejects this for v1.
- **Forcing all support interaction through a portal**: increases friction; reduces engagement, especially with academic/researcher audiences that value low-friction tools.
- **Building Slack UIs for structured ticket editing (modals, multi-step forms)**: Slack's UI primitives are weak for this. Customers and agents prefer the web UI for structure; Slack is for conversation.

---

## 3. Git-as-database for collaborative tools

Scree's "Git as primary store" approach has prior art worth studying.

### Sourcehut

Email-driven, Git-native development platform. Issues and patches are exchanged via email and stored in Git. The platform is opinionated about minimalism.

Relevant insights:
- **Git is genuinely usable as the substrate** for structured collaborative data, with careful tooling.
- **Email integration is hard and fragile** even for experienced operators; Sourcehut has documented the edge cases extensively.
- **The user audience self-selects toward technical users** who are comfortable with the model. This works for Sourcehut's audience; Scree's audience is broader, so the UI layer matters more.

Don't borrow Sourcehut's UI patterns directly — they assume a developer audience. Do borrow the data model patterns and the seriousness about email-integration edge cases.

### Radicle

Peer-to-peer code collaboration with Git-native issues, patches, and discussions. Demonstrates that Git can be the substrate for richer collaborative data than just code.

Relevant insights:
- **Git's data model accommodates structured collaboration with appropriate conventions** (specific file layouts, metadata schemas).
- **Offline-capable read access is genuinely valuable** for distributed teams.
- **Identity in a distributed Git world is via cryptographic keys**, which informs how identity is preserved in audit trails even without a central authority.

Scree is not distributed in the Radicle sense (there's a central GitLab instance), but the patterns for representing structured data in Git transfer.

### Gitea and Forgejo

Lightweight Git forges. Relevant mostly as foils to GitLab Ultimate: they show what a minimal forge looks like, which clarifies what Ultimate's additional features provide. Not direct prior art for Scree.

### Anti-patterns from Git-as-database systems

- **Pretending the index is the source of truth**: drift between index and Git causes problems. Always rebuild from Git; never trust index-only state.
- **Allowing the application to bypass Git for performance**: every write must go through Git so history is complete and tamper-evident. Performance optimizations live in the index, not in the primary store.
- **Insufficient schema discipline**: without schema validation, the data substrate degrades over time. Schema versioning and validation must be enforced from day one.

---

## 4. Authorization for collaborative tools

Scree's permission model spans GitLab-native RBAC and application-level relationship-based access control. Several pieces of prior art inform this.

### Google Zanzibar (paper) and implementations

Zanzibar is Google's internal authorization system, described in a 2019 paper. It defines a model for relationship-based access control (ReBAC) at Google scale. The model is general: tuples of (user, relation, object) define who has what relationship to what, and rules define how relations compose into permissions.

Open-source implementations:

- **SpiceDB** (AuthZed): mature, well-documented, opinionated ReBAC engine. Schema-based. Production-ready.
- **OpenFGA** (Auth0/Okta): similar model. Open governance. Also production-ready.
- **Permify, Warrant**: other implementations.

For Scree's service desk tickets (requester, watcher, assignee, owner relations), ReBAC is the natural model. The analyst should specify the access patterns; the architect should choose between SpiceDB and OpenFGA (or custom-build if the scope is genuinely small enough to not warrant a separate engine).

### What ReBAC handles well

- Multi-relation resources (a ticket has multiple users with different relations)
- "Friend of friend" patterns (assignee's team can also see)
- Negative relations (excluded users)
- Caveats and conditional permissions (time-limited access)

### What ReBAC complicates

- Tuple management at scale (every relation is a tuple; many tuples to maintain)
- Cache invalidation (changing relations must invalidate cached permission decisions)
- Reasoning about emergent behavior (rules compose in non-obvious ways)
- Operating yet another service

For Scree's scale (a few thousand external users, a few hundred internal, modest ticket volume), the ReBAC complexity is manageable but not zero. Custom build of a simple relation table is also viable if the relations are bounded (requester, watcher, assignee, owner — that's it).

### Authorization anti-patterns

- **Caching permission decisions for long periods**: revocations don't propagate. Short TTLs are required.
- **Trusting frontend permission checks**: frontend is hostile territory. Backend enforces.
- **Permission checks at view level only, not per-item**: aggregation views leak. Per-item checks are required.
- **Mixing permission and business logic**: hard to audit. Separate the permission engine from business logic.

---

## 5. WYSIWYG editors with markdown round-tripping

Scree's knowledge management UI requires WYSIWYG editing with markdown as the storage format. Several mature options exist.

### TipTap (ProseMirror-based)

Widely used in commercial products. Maintained, well-documented, large community.

- Markdown round-tripping via plugins
- Extensible model (custom node types, marks, commands)
- Collaboration features available (Yjs integration for real-time multi-user editing)
- Pricing model: free for OSS use, paid for some commercial features (the editor core is free)

### BlockNote (ProseMirror-based)

Newer, Notion-style block editor. Polished out-of-the-box. Smaller customization surface than TipTap.

- Markdown export and import
- Block-based UX (each paragraph, heading, list is a draggable block)
- Good fit if Notion-style UX is desired

### Milkdown (ProseMirror-based)

Markdown-first by design. Extensive plugin ecosystem.

### Lexical (Meta)

Newer, capable, growing ecosystem. Not yet as mature as TipTap.

### Quill, Slate, Draft.js

Older alternatives. Generally less recommended for new projects in 2026 (Draft.js is deprecated; Slate has had stability concerns; Quill is older but limited customization).

### Selection criteria for Scree

The architect should evaluate:

- Markdown round-tripping fidelity (does saving and reopening preserve content?)
- Table editing quality (Confluence users expect good table support)
- Paste-from-Word behavior (non-technical users paste from Word constantly)
- Image upload integration
- draw.io / diagrams.net integration capability
- Collaborative editing (yes/no, multi-user cursors)
- Accessibility compliance (WCAG 2.1 AA at minimum)
- Bundle size and performance
- Maintenance and community health

### Anti-patterns from editor choice

- **Building from scratch**: documented above. Don't.
- **Choosing based on demo videos rather than evaluation against requirements**: editors look great in demos and reveal issues in real use.
- **Underestimating paste-from-Word**: this is the single most common content-input path for non-technical users and is the area where many editors fail badly.

---

## 6. Migration from Atlassian

The migration pipeline has prior art from many organizations that have left Atlassian.

### Atlassian's own export tools

- Jira: REST API for export; XML backup format; CSV import support.
- Confluence: REST API; XML backup; HTML export.

These work but are slow at scale and have known edge cases (attachments, comments, custom fields, page macros).

### Third-party migration tools

Various vendors offer Atlassian migration services. None are particularly relevant for a custom-build destination, but their documentation enumerates the data structures and edge cases to handle.

### The actual hard part of migration

The technical migration (export → transform → import) is solvable. The hard part is curation: deciding what comes forward and what gets archived. This is non-technical effort that doesn't scale with engineering team size.

Insights from organizations that have done large Atlassian migrations:

- **Time-box curation strictly**. Open-ended curation never finishes.
- **Default to archive, require opt-in for migration**. Anything not explicitly curated by the deadline gets archived.
- **Migrate by team, not by content type**. Each team's curation is its own scope. Cross-team dependencies in content require coordination.
- **Map old IDs to new IDs publicly**. Many tools, documents, and people reference Jira ticket IDs and Confluence page URLs. A persistent mapping table prevents broken references after cutover.
- **Read-only archive is genuinely useful**. People need to look up old stuff occasionally. Keeping a read-only Atlassian instance for 1-2 years post-cutover is a common pattern.

### Anti-patterns from migrations

- **Aspirational migration scope**: "let's bring forward everything important." Defines no boundary; never finishes.
- **Parallel operation for an extended period**: dual entry, drift, ambiguity about source of truth.
- **No mapping of old IDs**: link rot affects every existing reference to migrated content.
- **Forgetting integrations**: third-party tools that consume Atlassian webhooks, OAuth integrations, browser extensions, etc., must be inventoried and either migrated or decommissioned.

---

## 7. Multi-channel customer support

Scree's external service desk has three customer-facing surfaces: email, web portal, public Slack channel. Multi-channel support is a well-studied problem.

### Zendesk, Intercom, Help Scout

Commercial multi-channel support tools. Relevant patterns:

- **Unified ticket view across channels**: regardless of how a customer contacted, agents see one record.
- **Channel as metadata**: the ticket records which channel originated it and which channels have activity.
- **Customer-side view across channels**: customer sees their own ticket history regardless of how they originally contacted.

Scree adopts these patterns. The `origins` field on a ticket tracks how it was created and through which channels it has been updated.

### Anti-patterns from multi-channel support

- **Channel-specific tickets**: same customer asking the same question via email and Slack produces two tickets. Bad.
- **Inability to merge or link related tickets**: duplicates accumulate.
- **Forgetting Slack/chat history when the ticket is closed**: customers expect their interaction history to be coherent. Snapshot capture at linking time partially addresses this; the rest is good UX showing where additional history lives.

---

## 8. Other relevant influences

### Inbox-zero patterns

Scree's agent UI should consider inbox-zero patterns for ticket triage: archive/respond/snooze/escalate as primary actions, with the queue presenting a clear "what's next" rather than overwhelming the agent with the whole backlog.

### Notion's database model

Notion's flexibility comes partly from its "everything is a database row" model. This is too far for Scree (the cost is high schema discipline burden on users), but the principle that *similar data structures benefit from similar UX* is worth keeping.

### Backstage (developer portal)

Spotify's Backstage is a developer portal that aggregates information from many systems. Relevant for the aggregation patterns: pulling data from multiple sources, presenting unified views, respecting source-system permissions.

### Datasette

Simon Willison's tool for publishing structured data. Relevant for the "read-only API over a structured dataset" pattern. Not a direct fit, but informs how Scree's index can be exposed for ad-hoc queries.

---

## Summary of borrowed and rejected patterns

### Borrowed from prior art

- Linear's opt-in-per-ticket Slack sync model
- GitLab's group/project permission inheritance
- Multi-channel ticket unification (Zendesk pattern)
- ReBAC for service desk relations (Zanzibar/SpiceDB/OpenFGA model)
- TipTap or equivalent for WYSIWYG with markdown round-tripping
- Persistent old-ID-to-new-ID mapping for migration

### Explicitly rejected from prior art

- Full bidirectional chat/ticket sync by default
- Auto-creation of tickets from chat heuristics
- Building a markdown editor from scratch
- Parallel operation of old and new systems for extended periods
- Open-ended migration curation
- Caching permission decisions for long periods

### Open evaluation questions for analyst/architect

- SpiceDB vs OpenFGA vs custom relation table
- TipTap vs BlockNote vs Milkdown
- Specific email integration library
- Archive strategy: read-only Atlassian instance vs static HTML export

---

**End of prior art evaluation.**
