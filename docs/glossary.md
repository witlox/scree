# Glossary

Plain-language definitions of the terms you'll meet in Scree. The full,
analyst-level vocabulary is in [Ubiquitous Language](../specs/ubiquitous-language.md);
this page is the short version for everyday use.

- **Space** — a GitLab project that holds knowledge pages (and the risks of that
  work). "Can I see this Space?" = "Can I read this GitLab project?"
- **Page / Doc** — a knowledge document: Markdown + YAML frontmatter in Git.
  Versioned, not stateful — there is no draft/published flag; the Git history is
  the record.
- **Governed path** — a page (e.g. policy, HR) that requires a **merge request**
  to change, instead of a direct save. Enforced by branch protection + CODEOWNERS.
- **Ticket** — a customer support request, however it arrived (web, email, Slack).
  Private to the requester and the support team unless promoted.
- **Community-visible** — a resolved ticket an agent has published to the public
  knowledge base as a **curated snapshot** (frozen at promotion, not the live
  thread).
- **Requester** — who a ticket is for, stored as an **opaque id** (no email/name in
  Git). The mapping to real contact details is kept outside Git and is the GDPR
  erasure target.
- **Agent** — a member of the support team who can work the queue and promote
  answers. A **desk lead** additionally sees orphan triage for their desk.
- **Risk** — a tracked threat, scored **5×5** (likelihood × impact) with a severity
  band, carrying a **ROAM** strategy.
- **ROAM** — Resolve, Owned, Accepted, Mitigated: the four ways to treat a risk.
- **Escalation** — promoting a project risk to an org-level duplicate that
  cross-references the original (which stays put).
- **Aggregation** — any cross-project view (portfolio rollup, cross-project risk
  register, community search). **It never reveals an item you couldn't open
  directly** — not its title, count, or score.
- **Gateway** — the single API service that enforces all permissions. There is no
  other enforcement point; nothing is decided in the browser.
- **Opaque id** — a stable, meaningless identifier (e.g. `ext-9f3a…`) used in place
  of PII so personal data stays out of Git.
- **Quarantine** — inbound email that couldn't be verified (or whose verified
  sender doesn't match the ticket it quotes) is held here for agent review rather
  than silently attributed.
- **Orphaned active** — an open risk/ticket whose owner or assignee lost access;
  flagged for a human to reassign, never auto-reassigned.
- **Graceful degradation** — when GitLab is unreachable, reads still serve from a
  local clone and writes are refused clearly (never silently dropped).
- **Crypto-shred** — making an encrypted ticket permanently unreadable by destroying
  its per-requester key (used on GDPR erasure).
