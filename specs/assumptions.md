# Scree — Assumptions

Explicit, falsifiable assumptions the design depends on. Each has a test (how we'd
know it is false) and an impact if it is. **★ = architecture-invalidating** if
wrong — the architect must validate these early.

---

| # | Assumption | How we'd falsify it | Impact if false |
|---|---|---|---|
| **A-1** | GitLab Ultimate self-managed remains the substrate and its REST/GraphQL API is stable enough to build on. | API breakage or licensing change. | Project premise shifts (DD-001). |
| **A-2 ★** | Keycloak supports token exchange (RFC 8693) for our gateway→GitLab flows. | Exchange flow can't be configured/issued. | Identity propagation (INV-ID-1) needs a redesign; GitLab audit loses the human actor. |
| **A-3 ★** | ~2–3k external customers can be Keycloak principals **without** consuming GitLab seats. | GitLab requires seats for ticket participation. | Cost/seat model breaks; portal identity needs rework. |
| **A-4 ★** | GitLab Advanced Search filters results by the **searching user's** permissions. | A search returns items the user can't open. | Internal aggregation can't lean on Advanced Search; more custom filtering needed. |
| **A-5 ★** | At this scale, **query-time per-item permission filtering** for aggregation is performant enough (no pre-partitioned per-user indexes). | Aggregation latency unacceptable under load. | INV-AGG enforcement strategy (permission-model §6) must change. |
| **A-6** | Git handles the resource volume with directory sharding; file-count per directory stays manageable. | Repo/dir performance degrades. | Need a sharding strategy / different layout (DD-002). |
| **A-7** | O365/Graph is the sole inbound mail path; the org does not own it (weaker sovereignty for email, accepted). | — (accepted limitation). | None new; documented in DD-019. |
| **A-8** | One public Slack channel; email-based Slack↔Keycloak mapping is reliable enough, and refuse-on-failure is acceptable. | Mapping fails often enough to frustrate users. | Slack capture friction; revisit mapping mechanism (OQ-A-016). |
| **A-9** | Markdown round-trips cleanly through the chosen ProseMirror editor. | Save→reopen loses or mangles content. | Editor choice/config rework (DD-016, OQ-X-002). |
| **A-10** | Big-bang cutover is acceptable; limited rollback is tolerable given pre-cutover validation. | Stakeholders require phased rollout. | Migration approach changes (DD-014). |
| **A-11** | Direct-commit default suits routine updates; only a small set of paths need MR review. | Compliance demands review on far more paths. | Friction rises; governance model revisited (DD-009). |
| **A-12** | ReBAC relations stay bounded (requester/watcher/assignee/owner). | New relation types proliferate. | A full ReBAC engine becomes necessary vs a custom table (OQ-X-001). |
| **A-13** | Critical = security/compliance category is a disciplined, stable trigger definition. | Categories get gamed or critical-ness needs nuance. | Webhook trigger redefinition (OQ-A-013 → OQ-HE-001). |
| **A-14** | Internal users are GitLab users; external customers are not — and this split is clean. | A class of users straddles both. | Principal model and permission composition revisited (OQ-A-004). |

---

The ★ assumptions (A-2, A-3, A-4, A-5) are the load-bearing ones. The architect
should spike them before committing to the architecture, and the docs-frontend
spike (PROPOSAL) is a natural place to validate A-4 and A-5 end-to-end.
