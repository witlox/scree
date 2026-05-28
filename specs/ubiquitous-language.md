# Scree — Ubiquitous Language

One term per concept, no synonyms. Code, endpoints, schemas, and specs use these
exact names. New term needed? Add it here first; if a concept is missing, that is
an analyst gap, not a coding decision.

---

## Core

| Term | Definition |
|---|---|
| **Resource** | Any stored artifact: a markdown file with YAML frontmatter in a GitLab repo. Has a `kind`. |
| **Kind** | The type discriminator of a Resource: `doc`, `ticket`, or `risk`. |
| **Space** | The unit of organization: one GitLab **project (repo)**. Permissions inherit from it. |
| **Owner** | The single accountable principal for a Resource. |
| **Reference** | A typed outbound link from one Resource to another Resource or a GitLab object. |
| **Audit** | The Git commit history of a Resource — author, timestamp, content delta. Not a separate field. |
| **Schema version** | Integer `schema_version` in frontmatter, present from first commit; governs validation/migration. |

## Kinds

| Term | Definition |
|---|---|
| **Doc** | A knowledge Resource. Has versions, not states. |
| **Ticket** | A service-desk Resource with relations and a visibility flag. |
| **Risk** | A Resource describing a risk, with category/likelihood/impact/score/strategy/review cadence. |
| **Category** (risk) | The risk's class: delivery, security, compliance, operational, or strategic. security or compliance ⇒ critical (fires the webhook). |
| **Project-level risk** | A Risk stored in its project's repo at `risks/`; lifecycle bounded by the project. |
| **Org-level risk** | A Risk stored in a dedicated org space (portfolio/security/compliance). |
| **Escalation** (risk) | Explicit duplication of a project-level risk into an org space, with a cross-reference. |

## Planning

| Term | Definition |
|---|---|
| **Planning item** | A GitLab-native epic/iteration/milestone — **not** a stored Scree Resource. |
| **Aggregation view** | A derived, read-only cross-source view (risk register, portfolio rollup, search results). |
| **Portfolio rollup** | A Planning aggregation above GitLab group scope (PI commitment, capacity vs load, dependencies). |

## Service desk

| Term | Definition |
|---|---|
| **Requester** | The principal who created/owns a Ticket's request. |
| **Watcher** | A principal granted visibility into a Ticket without ownership. |
| **Assignee** | The agent responsible for working a Ticket. |
| **Agent** | An internal user who triages and works tickets. |
| **Community-visible** | A Ticket flag (default off) making a resolved Ticket visible to the customer community. |
| **Origin** | The channel a Ticket was created through: email, web, Slack, or API. |

## Access & identity

| Term | Definition |
|---|---|
| **Principal** | Any actor: internal user, external customer, agent, operator, service account, or Slack-bot-on-behalf-of. |
| **Internal user** | Staff; authenticates via Keycloak; is a GitLab user. |
| **External customer** | An academic end user; authenticates via Keycloak; **not** a GitLab user. |
| **Operator** | An SRE/operator of the deployed system. |
| **Service account** | A non-human identity used for service-to-service calls. |
| **Token exchange** | RFC 8693 exchange of a user token for a downstream-scoped token, preserving human identity. |
| **ReBAC** | Relationship-based access control, used for ticket relations (requester/watcher/assignee/owner). |
| **Org tag** | Institutional-affiliation metadata on an external customer. **Not** a permission boundary in v1. |

## Indexing & integration

| Term | Definition |
|---|---|
| **Index** | A derived, rebuildable store powering aggregation/search. Never the source of truth. |
| **Scraper** | The indexer that walks accessible repos and updates the index. |
| **Batch trigger** | The hourly default indexing run. |
| **Manual trigger** | An authenticated on-demand re-index request. |
| **Critical webhook** | A GitLab webhook firing on changes to risks whose `category` is security or compliance, for near-real-time indexing. |
| **Gateway** | The single API and permission-enforcement point; all surfaces call it; no bypass. |
| **Snapshot capture** | Recording a Slack thread's content at the moment it is linked to a Ticket (no ongoing sync). |

## Process

| Term | Definition |
|---|---|
| **Direct commit** | The default update model: write straight to the main branch. |
| **MR-required path** | A path/resource where a merge request is mandatory (compliance-tagged, closed risks, designated docs). |
| **Curation** | The time-boxed migration decision of what content moves forward vs goes to read-only archive. |
| **Cutover** | The single big-bang switch from Atlassian to Scree. |
