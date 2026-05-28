# Scree — Context Graph

Bounded contexts, their dependency direction (acyclic), and the trust boundaries.
Contexts are defined in `specs/domain-model.md`; this fixes how they depend on
one another and where trusted meets untrusted.

## Dependency direction (arrows point to the dependency)

```
        ┌─────────────────────── clients ───────────────────────┐
        │  Web (htmx + React)   CLI   Slack adapter   Email adapter │
        └───────────────────────────┬───────────────────────────┘
                                     │  (all call the same API)
                                     ▼
                               ┌───────────┐
                               │  GATEWAY  │  single enforcement point
                               └─────┬─────┘
              ┌──────────────┬───────┼────────┬───────────────┐
              ▼              ▼       ▼        ▼               ▼
         ┌─────────┐   ┌──────────┐ │  ┌──────────┐    ┌──────────┐
         │ Access  │   │Knowledge │ │  │ServiceDesk│   │  Risk    │
         │ (authz, │   │  (docs)  │ │  │ (tickets) │   │          │
         │ identity│   └────┬─────┘ │  └────┬─────┘    └────┬─────┘
         │ audit)  │        │       │       │               │
         └────┬────┘        └───────┼───────┴───────┬───────┘
              │                     ▼               ▼
              │               ┌──────────┐    ┌──────────┐
              │               │ Indexing │◀───│ Planning │ (read-only views)
              │               └────┬─────┘    └──────────┘
              ▼                    ▼
        ┌──────────────────────────────────────────────┐
        │  Integration adapters (clients of the Gateway) │
        │  GitLab · Keycloak · O365/Graph · Slack · Vault · OpenFGA
        └──────────────────────────────────────────────┘
```

- **Gateway** depends on **Access** (to authorize) and on the domain contexts
  (Knowledge/ServiceDesk/Risk) to execute commands. It is the only inbound door.
- Domain contexts depend on **Access** (authority), **schemas**, and the
  **Integration** layer (to reach GitLab/etc.) — never on each other directly.
- **Planning** and **Indexing** are read-side/derived; they depend on Integration
  (GitLab planning objects) and feed aggregation views. Nothing depends on them
  for correctness (the index is rebuildable — INV-ST-2).
- **Migration** (not shown) is a one-shot pipeline that writes through the same
  domain contexts; it has no runtime dependents.
- Graph is **acyclic**: `schemas`/`platform` are leaves; Integration is leaf-ward;
  Gateway is the apex; Planning/Indexing hang off the read side.

## Trust boundaries

1. **Untrusted input → Gateway.** External customers, inbound email, and Slack
   payloads are untrusted. Everything crossing here is validated and authorized
   before use (INV-ACC-1, INV-EMAIL-1, INV-SLACK-1). Inbound email additionally
   requires DKIM/DMARC verification.
2. **Gateway → external systems.** Calls to GitLab/Graph/Slack/Vault/OpenFGA cross
   into systems Scree authenticates to (OIDC token exchange for GitLab; service
   creds from Vault). Downstream tokens are minimally scoped (INV-ID-1).
3. **Integration adapters are semi-trusted clients.** The Slack and email adapters
   call the Gateway like any other client and hold **no** privileged backend access
   (DD-006) — a compromised adapter cannot bypass authorization.
4. **Encryption boundary.** Encrypted content (sensitive spaces; tagged/born-
   encrypted tickets) is plaintext only inside the Gateway/authorized memory and
   the access-controlled index (INV-ENC-1/3); at rest in Git it is ciphertext.

## External dependencies and degraded modes

| Dependency | Used by | Degraded mode |
|---|---|---|
| GitLab | all writes, repo reads | reads from local clone; writes refused (INV-DEG-1) |
| Keycloak | all auth | no new logins; valid tokens honored to expiry (FM-3) |
| Vault (incl. Transit) | service creds, per-requester ticket keys | encrypted-ticket read/write degrades; user auth unaffected (FM-6) |
| OpenFGA | ticket authority + ListObjects | ticket authz unavailable → fail closed (INV-ACC-5) |
| O365/Graph | inbound/outbound email | inbound ticket creation fails visibly (FM-2) |
| Slack | capture/notify | capture unavailable; other origins unaffected (FM-7/8) |
| Object store | external attachments | ticket text still created; attachment retried (FM-14) |
