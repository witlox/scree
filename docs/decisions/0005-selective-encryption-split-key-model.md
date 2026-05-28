# ADR-0005: Selective encryption at rest with a split key model

- Status: accepted
- Date: 2026-05-28
- Deciders: build team
- Resolves: finding F-01 (ticket privacy), F-07 (page-level doc permissions)
- Context phase: analyst gate-1 resolution

## Context and Problem Statement

Tickets and docs are markdown files in GitLab repos, but per-ticket privacy and
"page-level permissions independent of project membership" cannot be enforced by
GitLab repo RBAC alone: anyone with repo read can clone and read the files,
bypassing the Gateway (finding F-01). Application-layer encryption at rest fixes
this — but encryption trades away the DD-002 properties (offline read, grep,
readable Git audit) for whatever it covers.

## Decision Drivers

- Protect genuinely-sensitive content without a Gateway bypass (F-01).
- Deliver page-level/space-level permissions independent of repo membership (F-07).
- Preserve DD-002 sovereignty/operability (offline read, grep) for the bulk.
- External customers (2–3k) must never receive decryption keys.

## Decision Outcome

**Selective encryption with a split key model.**

1. **Encrypt only the sensitive subset:** private ticket bodies, and designated
   sensitive doc/risk **spaces** (e.g. security, compliance, HR). Everything else
   stays cleartext Git, keeping offline-read, grep, and readable audit.
2. **Key model by audience:**
   - **Client-side recipient keys (age) — scoped at gate-2 (AR-01) to
     break-glass/DR/SOC content only.** Held out-of-band, readable offline from a
     clone when the online stack is down. General sensitive doc spaces are
     **Gateway-mediated** (Vault Transit, web-accessible) per ADR-0008 — that is
     what now delivers F-07 (page/space-level permissions independent of repo
     membership). See ADR-0008 for the authoritative key model.
   - **External-customer ticket bodies → cleartext-in-Git by default** (revised by
     ADR-0006). They are encrypted only when **(a)** sensitivity/compliance-tagged
     or **(b) born encrypted** (the create-time "encrypt" toggle), using a
     **per-requester** Gateway-mediated key (Vault) — never given to customers, and
     crypto-shreddable on erasure. F-01 for *cleartext* tickets is handled by
     constraining the desk repo to agents + Gateway-only access for non-agents (not
     by blanket encryption).
3. What is encrypted: the **body** and any sensitive frontmatter fields. Routing/
   permission metadata stays cleartext so the system can locate and authorize.

### Consequences

- Good: F-01 closed (no clone bypass for sensitive content); F-07 delivered;
  bulk content keeps DD-002 properties; external keys never leave the server.
- Bad / accepted:
  - For client-key content, **decryption is client-side**, so the Gateway is not
    the enforcement point or auditor for those reads (INV-ACC-1/INV-ID-3 are
    scoped to exclude authorized offline reads by existing key-holders).
  - **Revocation is rotation-based** for client-key content: a prior key-holder
    retains access to versions they could already decrypt. Acceptable for the
    internal-staff trust model; documented.
  - The **search index holds plaintext** for indexed sensitive content, so the
    index is a protected at-rest store covered by INV-AGG (INV-ENC-3).
  - Encrypted content cannot be textually merged (worsens FM-15 for those files).

## Open follow-up (architect)

- **OQ-X-009:** choose the encryption tooling/topology — git-crypt vs age vs SOPS
  for client-key content; Vault transit vs envelope encryption for Gateway-
  mediated content; key rotation and recipient management.
