# Scree

**Git-native knowledge, planning, and service desk.**

A custom application layer on top of GitLab Ultimate self-managed, providing knowledge management, external customer service desk, and cross-project portfolio/risk aggregation. All primary data stored as markdown with YAML frontmatter in Git repositories.

---

## Status

**Pre-analyst seed.** The design conversation has produced this seed package. The analyst phase is next.

## Navigation

### For stakeholders
- **[`docs/SUMMARY.md`](docs/SUMMARY.md)** — design summary for stakeholders, non-technical-friendly

### For the analyst
- **[`specs/SEED.md`](specs/SEED.md)** — primary input, defines problem and constraints
- **[`docs/analysis/design-conversation.md`](docs/analysis/design-conversation.md)** — distilled design conversation for context
- **[`docs/analysis/design-decisions.md`](docs/analysis/design-decisions.md)** — design decisions with rationale and trade-offs
- **[`docs/analysis/prior-art.md`](docs/analysis/prior-art.md)** — prior art evaluation
- **[`docs/analysis/open-questions.md`](docs/analysis/open-questions.md)** — open questions for analyst, architect, and stakeholder resolution

### For Claude Code
- **[`CLAUDE.md`](CLAUDE.md)** — project-wide context loaded on every session
- `.claude/CLAUDE.md` — workflow router: how the active role/mode is inferred and reported
- `.claude/roles/` — diamond workflow role profiles
- `.claude/guidelines/`, `.claude/coding/` — shared engineering, BDD, language, and CI standards

## Workflow

This project uses the **diamond workflow**: analyst → architect → adversary → implementer → auditor → adversary → integrator. See related projects (Kiseki, Ghyll, Kith, Pact) for reference implementations.

There is no activation step. The active role (mode) is **inferred from the interaction and the current state of the repo**, and Claude reports which mode it is operating in at the start of a turn. See `.claude/CLAUDE.md` for the routing rules. The next mode is **analyst**, consuming `specs/SEED.md` as primary input.

## What's reused vs. built

**Reused from GitLab Ultimate (no custom work):**
- Code hosting, CI/CD, MRs, repo permissions
- Issues, epics, iterations, milestones for engineering work
- Audit events, compliance frameworks, advanced search

**Built custom:**
- Knowledge management UI (replacing Confluence)
- External customer service desk portal (replacing Service Desk for external use)
- Portfolio and risk aggregation views (filling gaps in GitLab)
- API gateway with single permission enforcement point
- Slack and O365 integrations
- Atlassian migration pipeline

## Constraints

See `CLAUDE.md` for the full list. Briefly:

- GitLab Ultimate (self-managed) as substrate
- Keycloak for identity (OIDC)
- Vault for service credentials
- O365 for email
- Slack for chat (one public community channel with external customers)
- Markdown + YAML frontmatter in Git for primary data
- API-first; single enforcement point for permissions
- Monorepo for the custom layer
- OpenTelemetry for observability

## License

[To be determined]

## Related projects

- **Kiseki**: distributed storage system (same author, similar workflow)
- **Ghyll**: diamond workflow reference implementation
- **Kith**: distributed shell agent (same author, similar workflow)
- **Pact**: configuration management (same author)

## Naming

A *scree* is a slope of accumulated rock fragments at the base of a cliff. The metaphor: organizational artifacts (docs, tickets, risks, plans) accumulate as a pile that has shape and structure if you read it right. The system makes the pile navigable.
