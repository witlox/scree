# ADR-0002: Backend language and framework — Python + FastAPI

- Status: accepted
- Date: 2026-05-28
- Deciders: build team, head of engineering
- Resolves: OQ-X-003
- Context phase: ratified ahead of architect phase

## Context and Problem Statement

SEED OQ-X-003 framed the backend choice as Rust vs Go, to be decided by the
organization's stack expertise. The build team added Python as a candidate.
The backend is integration-heavy, I/O-bound glue at modest scale (~150
internal, 2–3k external users): an API gateway doing OIDC token exchange, plus
GitLab / Microsoft Graph / Slack / git clients, an indexer, and a ReBAC layer.

## Decision Drivers

- Integration ecosystem fit (the system is mostly API glue)
- Team expertise and bus factor (shared-ownership team build)
- I/O-bound, not CPU-bound — raw performance is not the constraint
- Velocity for a large surface area

## Considered Options

- **Python + FastAPI**
- **Go** (single binary, strong typing, SpiceDB/OpenFGA are Go)
- **Node + TypeScript** (one language across the stack)
- **Rust** (performance, strong type system)

## Decision Outcome

Chosen option: **Python + FastAPI**.

Mature integration libraries across the board (`python-gitlab`, `msgraph-sdk`,
`slack-sdk`, `Authlib` for OIDC/token-exchange, `pygit2`); async handles the
I/O-bound concurrency well despite the GIL; strong team fluency; and an
optional path to near-free internal admin UIs. Rust over-indexes on
performance the system does not need. Go is viable but Python wins on team fit
and library breadth. Node would unify the language but competes poorly on
backend merits for long-lived services.

### Consequences

- Good: development velocity, library breadth, hiring pool, bus factor.
- Bad: weaker compile-time guarantees than Go/Rust. Mitigate with
  `mypy --strict`, Pydantic at boundaries, and enforcing/​testing the
  load-bearing permission invariant at the single gateway choke point.
- Heavier runtime than a static Go binary; managed via slim, non-root images.

## Notes

The frontend is TypeScript regardless (ADR-0003), so this is a two-language
stack by design.
