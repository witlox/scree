# Scree — Project Context

This file is loaded by Claude Code on every session, regardless of role profile. It provides project-wide context that role-specific profiles in `.claude/CLAUDE.md` build on.

---

## Project identity

**Name**: Scree
**Tagline**: Git-native knowledge, planning, and service desk for an org leaving Atlassian
**Naming rationale**: A scree is a slope of accumulated rock fragments at the base of a cliff. The metaphor: organizational artifacts (docs, tickets, risks, plans) accumulate as a pile that has shape and structure if you read it right. The system makes the pile navigable.

## What Scree is

A custom application layer on top of GitLab Ultimate self-managed, providing:

1. **Knowledge management UI** suitable for non-technical users (replacing Confluence)
2. **External customer service desk portal** with email/web/Slack integration (replacing Atlassian Service Desk for external use)
3. **Cross-project portfolio and risk aggregation views** (filling GitLab's gap for SAFe-style portfolio and risk management)

Plus the foundational pieces: API gateway, permission engine, indexers, integrations, schemas, migration pipeline.

## What Scree is not

- A replacement for GitLab's existing features (issues, epics, iterations, code, CI). Those are reused.
- A separate identity store (Keycloak is authoritative).
- A separate secrets store (Vault is authoritative).
- A fully disconnected-operation system (graceful degradation only; full offline is out of scope).

## Workflow

This project uses the **diamond workflow**: analyst → architect → adversary → implementer → auditor → adversary → integrator. Each phase has a role profile in `.claude/roles/<role>.md`. There is no activation step: the active role (mode) is **inferred from the interaction and the current state of the repo**, and reported at the start of a working turn. See `.claude/CLAUDE.md` for the routing rules.

The workflow protocol references and graduation criteria are defined in each role file. The pattern matches the user's prior projects (Kiseki, Heddle, Kith, Pact, Ghyll) — see those repos for reference implementations.

## Current phase

**Release engineering / v1 cutover prep.** The diamond has cycled through every
role at least once: the analyst specs, architecture, ADRs, backend (`api/`) and
frontend (`web/`) are built; adversary gates (analyst, architecture, frontend,
impl 1–12) and the auditor fidelity index are recorded under `specs/findings/`
and `specs/fidelity/`; the integrator returned a **GO** verdict
(`specs/integration/readiness.md`).

What's standing up now is the delivery substrate: one-image Docker build, mdBook
docs → GitHub Pages (generated from specs/features/code by `docs/build.py`),
grouped Dependabot, a Wednesday-evening release (version `YEAR.ADR-COUNT.COMMIT-COUNT`),
and a Helm chart (`charts/scree/`).

The remaining substantive gate is **live-infra verification** — exercising the
real Keycloak/GitLab/Vault/OpenFGA boundaries and a browser, which the mocked
fast tier and nightly `@contract` tier cannot prove. Open follow-ups are tracked
in `specs/fidelity/gaps.md` and `docs/analysis/open-questions.md`.

## Constraints (project-wide)

These apply regardless of role. They are not negotiable in any phase without explicit revisit and stakeholder ratification.

### Technical
- **GitLab Ultimate self-managed** is the primary substrate
- **Keycloak** is the identity provider; OIDC tokens are the auth currency
- **Vault** holds service credentials (not in user-facing auth path)
- **O365 via Microsoft Graph** is the email transport
- **Slack** is the chat platform (one public community channel with customers; no Slack Connect; no per-customer private channels in v1)
- **Markdown with YAML frontmatter in Git** is the primary data substrate
- **Permissions are layered**: GitLab repo-level + application-level ReBAC for service desk tickets
- **API-first**: single gateway is the only enforcement point
- **OpenTelemetry** for observability

### Architectural
- **Monorepo** for the custom layer
- **Three-tier trigger model** for indexing: hourly batch + manual + critical-only webhook
- **Update model**: direct commit default, MR-required for compliance-tagged paths
- **External attachments**: object storage (not Git LFS) for service desk attachments

### Workflow
- **Big bang migration** from Atlassian (not phased rollout)
- **Time-boxed curation** with hard deadline; non-curated content goes to read-only archive
- **Team build** with shared ownership (bus factor managed by collective ownership)

## Stakeholders

- **Head of Engineering**: executive sponsor, scope cut authority, vendor exit timeline owner
- **Internal users (~150)**: mixed engineers and non-technical staff
- **External customers (~2000-3000)**: academic researchers, individual users
- **Build team**: shared ownership across multiple engineers
- **Operations / SRE**: operators of the deployed system
- **Compliance / audit**: stakeholders for risk register and audit trail features (specific requirements TBD via OQ-HE-005)

## User values applied to this project

The user has stated values that should inform decision-making:

1. **Decompose before deciding** — break complexity into tractable pieces before acting
2. **Trade-offs are fundamental** — acknowledge costs explicitly; optimize across dimensions
3. **Mutual optimization** — outcomes that benefit both self and others
4. **Calibrated fairness, not performative**
5. **Proportionate honesty** — share what's relevant; don't overshare
6. **Pragmatism executes, elegance orients** — ship what works; discuss elegance as direction
7. **Diversity creates resilience** — value perspectives beyond your own
8. **Structural skepticism** — question whether systems serve their stated purposes
9. **Sovereignty and autonomy** — people and communities should control what is theirs

These values manifest in design decisions: Scree exists because of #8 (questioning Atlassian's cloud-only forcing function) and #9 (controlling org data). The big-bang migration and per-repo risk split reflect #6 (pragmatism). The aggregation permission invariant and audit trail reflect #2 and #5 (acknowledging the trade-off and being honest about scope).

## Conventions

- All design artifacts in markdown
- All structured data in YAML frontmatter or YAML/JSON files
- All commits signed where possible (operator-level audit trail)
- Linear history preferred; merge commits acceptable for MRs
- Conventional commits format for commit messages
- ADRs (when produced by architect) follow MADR template

## References

- Kiseki repo (distributed storage system, same author): structural reference for SEED format and workflow profiles
- Ghyll repo (same author): reference for diamond workflow role definitions
- Kith repo (same author): reference for monorepo structure

---

**End of project context.**
