# Scree — Design Proposal for Group Discussion

**Status**: Proposal for discussion
**Audience**: Engineering team, head of engineering, and any stakeholders invited to the design review
**Purpose**: Surface the proposal, the trade-offs, and the open questions for collective decision-making before committing to build

---

## TL;DR

We are proposing to replace the Atlassian stack (Jira, Confluence, Service Desk) with a custom application layer built on top of our existing GitLab Ultimate self-managed instance. All primary data — docs, tickets, risks, plans — would be stored as markdown files with YAML frontmatter in Git repositories. The system integrates with our existing Keycloak, Vault, O365, and Slack infrastructure.

The custom build is deliberately scoped to three gaps that GitLab Ultimate does not fill: a knowledge management UI for non-technical users, an external customer service desk portal, and cross-project portfolio and risk aggregation views. Everything else GitLab already provides.

This document is a proposal, not a decision. It exists to provoke discussion, surface objections, and identify open questions before commitment.

---

## Why we are considering this

### The forcing function

Atlassian is moving Jira, Confluence, and Service Desk to cloud-only. Self-managed (data-center) licenses are being phased out. The cloud terms involve pricing the team finds extractive and operational characteristics the organization finds limiting (no self-managed operation, limited data sovereignty, mandatory upgrade cadence, no offline access).

If we do nothing, we end up on cloud Atlassian at materially higher cost and with reduced control. This is the status quo path.

### What we have that makes alternatives plausible

- GitLab Ultimate self-managed, already owned
- Keycloak for identity
- Vault for secrets
- O365 for email
- Slack for chat, including a public community channel where external academic customers interact with staff and each other
- An engineering team that has built complex systems using AI-assisted coding in this organization
- OpenTelemetry stack for observability

GitLab Ultimate is the key piece. It already provides issues, epics with multi-level hierarchy, iterations, roadmaps, advanced search, audit events, compliance frameworks, and much more. Most of what people use Jira for, GitLab already does.

### What GitLab Ultimate does not do well

Three things, which is the scope of the custom build:

1. **Knowledge management UI for non-technical users**. GitLab Wiki is workable for engineers and inadequate for marketing staff, PMs, and researchers. Confluence sets the bar.
2. **External customer service desk portal**. GitLab Service Desk is "email creates an issue," per-project. For 2000-3000 academic customers expecting a real support portal experience, this is insufficient.
3. **Cross-project portfolio and risk aggregation**. GitLab's epics are group-scoped, not portfolio-scoped. Risk management at the org level cuts across projects in ways GitLab does not model natively.

Everything else (code, CI, MRs, repo permissions, audit, group hierarchy) we reuse.

---

## What the system would do

### For internal users (~150)

- **Read and write docs** through a WYSIWYG editor that produces clean markdown. Page templates, meeting notes, decisions, action items, draw.io diagrams, search across all accessible docs.
- **Manage planning items** at portfolio/ART level (above what GitLab epics handle). View dependencies, capacity vs. load, PI commitment status.
- **Manage risks** at project level (in the project repo) and at org level (in dedicated repos). Aggregation views for leadership.
- **Service desk agents** triage and respond to customer tickets across email, web portal, and Slack origins, all unified in one interface.

### For external customers (~2000-3000 academic users)

- **Submit tickets** via email, web portal, or by flagging messages in the public community Slack channel
- **View their own tickets** through a web portal with login (Keycloak-authenticated)
- **Reply to tickets** via the portal or by email reply (threading preserved)
- **Search a community knowledge base** of resolved tickets that have been made community-visible
- **Continue using the public Slack channel** for community discussion and informal support

### For operators

- **Standard observability** via OpenTelemetry traces, metrics, and logs
- **Local-clone read access** to all docs/risks/tickets they have permission to see during GitLab outages
- **Git as audit trail** — every change has author, timestamp, content delta, preserved indefinitely

---

## How the system would work

### Data model

Every resource (doc, ticket, risk, planning item) is a markdown file with YAML frontmatter in a GitLab repository.

```yaml
---
id: risk-2026-001
schema_version: 1
title: Atlassian cloud-only forcing function creates vendor lock-in
likelihood: high
impact: high
score: 9
strategy: mitigate
owner: platform-team-lead
review_by: 2026-06-01
affects:
  portfolios: [engineering-platform]
mitigations:
  - gitlab.example.com/platform/atlassian-replacement#42
---

The narrative description of the risk goes here as markdown body...
```

This pattern applies uniformly across resource types. Schema differs by type; structure is consistent.

### Integration architecture

```
                       ┌──────────────────┐
                       │    Keycloak      │  identity (OIDC)
                       └────────┬─────────┘
                                │
                                │ tokens
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
   ┌────────┐             ┌──────────┐            ┌─────────┐
   │  Web   │             │   CLI    │            │  Slack  │
   │frontend│             │  client  │            │   bot   │
   └────┬───┘             └────┬─────┘            └────┬────┘
        │                      │                       │
        └──────────────────────┼───────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    API Gateway      │  single enforcement point
                    │  (authz, audit,     │  for all permissions
                    │   business logic)   │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
   ┌────────┐            ┌──────────┐           ┌──────────┐
   │ GitLab │            │   O365   │           │  Vault   │
   │ (data, │            │  (email) │           │ (secrets)│
   │  repos)│            │          │           │          │
   └────────┘            └──────────┘           └──────────┘
                               
                    Plus: indexer (hourly batch + manual + 
                    critical-webhook) maintains derived 
                    views for cross-project queries.
```

### Permissions

Layered model:

- **Coarse-grained** (most resources): inherited from GitLab repo/group membership, mapped from Keycloak groups via OIDC.
- **Fine-grained** (service desk tickets only): relationship-based access control — requester, watcher, assignee, owner — enforced by the API gateway.

The single enforcement point is the API gateway. Frontend, CLI, Slack bot, email service — all call the same API. No bypass paths.

For aggregation views (cross-project risk register, portfolio dashboards), the gateway filters results per-item by the requester's authority. The invariant: **you never see aggregated data that includes items you couldn't see directly**. This is treated as load-bearing.

### Trigger model for indexing

Three triggers, each with a clear purpose:

1. **Hourly batch**: default cadence. Catches everything within the hour.
2. **Manual trigger**: authenticated users can request immediate re-scrape of a project.
3. **Critical-severity webhook**: only fires for resources tagged `severity: critical`. Near-real-time propagation for the small number of cases where minutes matter.

Webhook fails → batch catches it. Batch fails → manual trigger and critical webhook still work. Triple-redundant for the cost of one fast path.

### Slack integration

One public community channel where external customers interact with staff and with each other.

- **Emoji-based ticket creation**: react to a thread with `:ticket:` → bot creates a draft ticket from the thread, agent reviews and confirms.
- **Slash-command linking**: `/link-ticket NNN` in a thread → attaches thread snapshot to existing ticket NNN. Permission-respecting autocomplete.
- **No bidirectional sync**: snapshot at link time only. If more captures needed later, re-link.
- **Tickets default to requester-private** even when spawned from public threads. Explicit promotion to community-visible.

This matches Linear's well-tested pattern. The deliberate narrow scope matches our team's chat-workflow experience.

### Migration

Big bang cutover. Migrate fully, drop non-relevant content per team curation, archive the original Atlassian instance as read-only.

The hard part is curation: every team reviewing what comes forward. This is time-boxed with a hard deadline; non-curated content defaults to archive.

---

## Trade-offs we are accepting

Honest about what this costs us.

### What we gain

- **Sovereignty**: we own the data substrate, the operational characteristics, and the evolution path
- **Cost reduction over time**: GitLab Ultimate (already owned) + engineering investment replaces ongoing Atlassian licensing
- **Fit-to-workflow**: the system matches our actual workflow, not a generic vendor model
- **Audit trail by construction**: Git history is tamper-evident
- **Partial offline access**: read access from local clones during GitLab outages
- **Composable**: same data substrate for all resource types simplifies cross-cutting concerns
- **No third-party data sharing**: customer data stays entirely within infrastructure we control

### What it costs us

- **Engineering investment**: building this is substantial work, even with AI-assisted coding
- **Operational responsibility**: incidents are ours to handle; we cannot escalate to Atlassian support
- **Long-tail feature requests**: every team has That One Workflow they will eventually request
- **Migration risk**: big bang cutover has limited rollback options if it goes badly
- **WYSIWYG editor edge cases**: paste-from-Word, complex tables, accessibility — known hard problems we own once we ship
- **Email transport dependency on O365**: we don't own this; if O365 is down, inbound email fails
- **External customer ticket submission has multiple online dependencies**: this is the least resilient operation in the system

### What we are not promising

- **Feature parity with Atlassian**: some Confluence macros, some Jira features will not be replicated
- **Friction-free migration**: big bang has costs; expect a transition period
- **Replacement of social processes**: risk management, planning, knowledge capture require human discipline no system provides
- **"AI-assisted coding makes this trivial"**: AI assistance reduces effort substantially but does not eliminate operational, integration, and UX work, which consumes most of any system's lifecycle cost

---

## Alternatives we considered

### A. Migrate to cloud Atlassian, accept the cost

**Pro**: zero engineering investment, known operational characteristics, immediate
**Con**: extractive pricing, loss of self-managed control, no offline access, vendor lock-in deepens
**Verdict**: rejected as the status quo path; this is what we are trying to avoid

### B. Adopt open-source replacements (Plane/OpenProject + Outline/BookStack + Zammad/FreeScout)

**Pro**: less engineering work than custom build, established communities, defined feature sets
**Con**: multiple tools to integrate, multiple data models to bridge, each tool brings its own UX assumptions that may not match our workflow, integration with Keycloak/Vault/GitLab/O365/Slack done multiple times
**Verdict**: considered. Real option. The decisive factor against: integration work is significant; we end up operating multiple systems with different operational characteristics; the cross-project aggregation gap remains unsolved.

### C. Custom build from scratch without leveraging GitLab Ultimate

**Pro**: full design freedom
**Con**: rebuilds substantial functionality GitLab Ultimate already provides (issues, epics, search, audit, compliance frameworks); a much larger project
**Verdict**: rejected because Ultimate's investment already covers most of the substrate

### D. Custom build on top of GitLab Ultimate (proposed)

**Pro**: reuses Ultimate's investment, scoped narrowly to gaps Ultimate doesn't fill, single substrate simplifies operations, fits our workflow precisely
**Con**: engineering investment, operational responsibility, migration risk
**Verdict**: this is the proposal

The decision between B and D is the actual choice. Both are real options.

---

## Effort estimation

We are deliberately not providing time estimates because they are unreliable for greenfield work. Instead, **relative effort** against a baseline "docs-frontend spike" unit (one working WYSIWYG editor with API and permission filtering for one resource type):

| Component | Relative effort |
|-----------|----------------|
| Backend API gateway, indexer, permission engine | 3-4× spike |
| Docs frontend (full WYSIWYG, hierarchy, search) | 2-3× spike |
| External customer portal | 4-5× spike |
| Internal admin UIs (planning, risks, agent queues) | 1-2× spike |
| Migration pipelines (Jira and Confluence, each) | 2× spike |
| Email integration (O365 Graph) | 1-2× spike |
| Hardening, security review, rollout | 2-3× spike |

**The spike is the recommended first deliverable**. It calibrates the unit and validates the architecture for the highest-uncertainty piece. If the spike takes substantially longer than expected, the full project estimates scale accordingly. This is a meaningful early signal we should not ignore.

---

## Risks worth discussing

### Likely-and-painful

- **Migration curation never finishes**: open-ended content curation has a known failure mode. Mitigation: time-boxed curation with hard deadline.
- **Permission leakage in aggregation views**: well-known failure mode for systems that aggregate cross-source data. Mitigation: treat the aggregation permission invariant as load-bearing, test exhaustively.
- **External customer portal underdelivers polish**: customer-facing UIs need more polish than internal tools. Mitigation: explicit narrow scope for v1, user testing before cutover.
- **WYSIWYG editor edge cases frustrate users**: paste from Word, complex tables, accessibility. Mitigation: use mature ProseMirror-based library; user testing during build.

### Possible-and-significant

- **Big bang cutover reveals migration gaps post-cutover**: limited rollback. Mitigation: thorough pre-cutover validation gates; parallel read access to Atlassian archive during stabilization.
- **Effort estimates were optimistic**: AI-assisted coding does not eliminate operational and UX work. Mitigation: the docs-frontend spike calibrates the unit; if the spike slips, the project plan slips.
- **Email integration is fragile**: parsing edge cases, threading edge cases. Mitigation: use mature libraries; agent capability to manually merge tickets when threading fails.

### Lower-risk-but-named

- **GitLab Ultimate licensing changes adversely later**: same risk profile as the current Atlassian situation but for one product. Accept and revisit if it occurs.
- **Vault outage affects service operations**: degrades service-to-service auth, not user login. Standard Vault HA configuration mitigates.

---

## Open questions for this discussion

The team should weigh in on these. Some require head-of-engineering decision; others are open for the group.

### Strategic

- **Do we accept the engineering investment vs. the alternatives** (cloud Atlassian, OSS stitch-together)?
- **What is our timing pressure**? When does Atlassian self-managed actually end for us? Does this dictate a faster or slower build?
- **Should we disclose this initiative to Atlassian for negotiation leverage**, or keep it internal until commitment?

### Scope and approach

- **Should the docs-frontend spike happen first** as proposed, before committing to the full build?
- **Is the deliberate narrow Slack integration scope acceptable**, or do we need more (e.g., per-customer private channels, ongoing thread sync)?
- **Is the individual-customer-with-org-tag model sufficient**, or do we need multi-user customer organizations from v1?

### Migration

- **What are the pre-cutover validation gates** that prove we are ready?
- **What are the curation criteria** for "non-relevant" content?
- **Read-only Atlassian instance kept indefinitely on a reduced license** vs. **static HTML export and full decommission**?

### Governance

- **Who decides scope cuts** when they happen (and they will)?
- **What MR-required paths do compliance and security want enforced** beyond what we have proposed (compliance-tagged content, closed risks, designated doc paths)?
- **Are there compliance regime constraints** on risk register format, audit trail format, data retention?

### Concerns we are anticipating

- **"This sounds like we are rebuilding the world."** Response: scope is deliberately narrow. We reuse GitLab Ultimate aggressively; we build only the three substantive gaps. The components list looks long because we are being explicit about every piece; in practice many are small.
- **"What if it takes way longer than expected?"** Response: the spike-first approach gives us an early signal. If the spike is much harder than expected, we revisit before committing to the full build. The cost of an unsuccessful spike is bounded.
- **"What about the people who like Confluence/Jira?"** Response: real concern. Some workflows will need to change. User testing during the build, training around cutover, and the read-only archive of historical content all mitigate. We should expect some user friction during transition.
- **"What if the team that built it leaves?"** Response: build is a team activity with shared ownership and the same workflow used for other systems in the organization. No single engineer is bus-factor-1. The architecture, decisions, and rationale are all documented as we go.

---

## What we would do next

If the team agrees to proceed:

1. **Run the docs-frontend spike** as the first deliverable. ~1 unit of effort. Validates the editor, API gateway, permission filtering, and Git-backed storage end-to-end for one resource type.
2. **Run the analyst phase** of the workflow against the SEED material. Produces formal specifications, ubiquitous language, invariants, failure modes, feature scenarios.
3. **Stakeholder ratification** of open questions (severity definitions, portal feature set, pre-cutover gates, curation criteria, etc.).
4. **Architect phase** designs the concrete architecture (component boundaries, language choices, deployment topology, library choices).
5. **Implement in slices** following the workflow, with regular reviews.
6. **Migration tooling and curation phase** runs in parallel with later implementation slices.
7. **Cutover** after pre-cutover validation gates are met.

If the team does not agree to proceed, we still need a decision about what we do about Atlassian. The status quo path is migrating to cloud Atlassian and accepting the cost. The OSS-stitch option remains as a fallback.

---

## What we are asking from this discussion

A decision: **proceed to spike**, **proceed to spike with modifications**, **explore the OSS-stitch alternative more thoroughly first**, or **migrate to cloud Atlassian and accept the cost**.

If "proceed to spike," we need:

- Sign-off from head of engineering on the scope and approach
- A spike timeline agreement (when does it deliver, what counts as success)
- Initial assignment of team members
- Decision on how the spike result triggers the next-phase commitment

If "explore OSS alternatives first," we need:

- Agreement on what we are evaluating against (what is the bar for "good enough"?)
- Timeline for that evaluation
- Who runs it

If "migrate to cloud Atlassian," we need:

- Acknowledgment of the cost and the loss of self-managed control
- Timeline for the cloud migration

---

## Appendix: navigating the supporting documents

For team members who want to go deeper:

- **`specs/SEED.md`**: the analyst seed; the formal starting point for the workflow. Read this if you want to see the problem statement, constraints, and hard questions in their canonical form.
- **`docs/analysis/design-conversation.md`**: distilled design conversation. Read this for the reasoning behind decisions.
- **`docs/analysis/design-decisions.md`**: 21 decisions with rationale, alternatives, and consequences. Read this if you want to know why we chose X over Y.
- **`docs/analysis/prior-art.md`**: evaluation of prior art (GitLab Ultimate features, Linear's Slack integration, ReBAC implementations, WYSIWYG editor libraries, migration patterns). Read this if you want to know what we learned from others.
- **`docs/analysis/open-questions.md`**: structured list of open questions with proposed owners. Read this if you want to see what is unresolved.

---

**This document is a proposal. The decision is the group's to make.**
