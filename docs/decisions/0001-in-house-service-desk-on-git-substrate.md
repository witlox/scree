# ADR-0001: Build the service desk in-house on the Git substrate

- Status: accepted
- Date: 2026-05-28
- Deciders: build team, head of engineering
- Context phase: ratified ahead of architect phase

## Context and Problem Statement

Analysis established that the **external customer service desk is the only
component that forces a custom server tier** into existence — internal users
are GitLab users and GitLab Advanced Search already does permission-filtered
cross-project search for them. That raised the question: rather than build the
service desk, can we slot in a mature open-source helpdesk (Zammad, Chatwoot,
FreeScout, OTOBO)?

## Decision Drivers

- DD-002: markdown + YAML frontmatter in Git as the single primary substrate
- DD-006: a single API gateway as the sole permission enforcement point
- DD-008: cross-resource aggregation (risk register / portfolio) over a
  unified store
- Avoiding open-core lock-in — the organization is leaving Atlassian precisely
  to escape extractive licensing

## Considered Options

- **A. Build in-house** on the Git substrate
- **B. Slot in an OSS helpdesk** as a parallel silo
- **C. Split the substrate** — Git for docs/risk/planning, a helpdesk for tickets

## Decision Outcome

Chosen option: **A — build in-house**.

A slot-in helpdesk satisfies the *feature* checklist but violates the three
founding decisions: it stores tickets in its own relational DB (breaks DD-002),
exposes its own API and permission model (breaks DD-006 — two enforcement
points), and silos ticket data away from cross-resource aggregation (breaks
DD-008). It also does **not** remove the aggregation build, which has no OSS
equivalent, so it trades away the foundation without removing the hardest
remaining work. Open-core helpdesks (SSO/portal/SLA behind paid tiers) risk
re-creating the lock-in the project exists to escape.

### Consequences

- Good: unified Git substrate, single enforcement point, aggregation works,
  no new vendor dependency, no second operational system.
- Bad: the service desk is the highest-cost and highest-risk custom component
  (email threading, ticket ReBAC, external identity at 2–3k users, portal
  polish) and it is entirely ours to own.
- The load-bearing aggregation permission invariant (DD-008) lives here —
  treat it accordingly in specs and tests.

## Notes

GitLab Service Desk solves a chunk of the email-threading problem *if* tickets
live as GitLab issues. We consciously decline that in favor of the md-in-Git +
ReBAC model. The architect must still decide the email approach (ADR pending).
