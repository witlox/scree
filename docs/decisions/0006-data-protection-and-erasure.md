# ADR-0006: Data protection & erasure model

- Status: accepted
- Date: 2026-05-28
- Deciders: build team
- Resolves: OQ-HE-005, OQ-HE-008 (compliance posture); finding follow-on to F-01
- Context phase: architect (front-loaded security/compliance)

## Context and Problem Statement

External customers (the Jira Service Management population we're replacing) are
individuals whose tickets carry PII, so GDPR right-to-erasure (Art. 17) applies.
But the substrate is immutable Git (DD-002): history is forever and clone-
everywhere. True byte-level erasure conflicts with that. We need an erasure model
that is honest, achievable, and **no weaker than the incumbent** without
over-engineering.

How does Atlassian/JSM do it today? **Anonymization, not content deletion** — the
account's personal-data fields are scrubbed and content is reattributed to a
"former user"; free-text bodies are not auto-scrubbed (handled manually). That is
the realistic industry bar.

## Decision Drivers

- "We can't have better guarantees than GitLab" — don't promise stronger-than-
  substrate confidentiality/erasure.
- Keep **as little data as possible outside Git** (sovereignty/operability).
- GDPR erasure must be operable for routine DSARs, not a heroic event.

## Decision Outcome

**Anonymization-based erasure + a minimal out-of-Git identity directory +
selective/opt-in encryption — all bounded by the GitLab substrate.**

1. **Identity directory is the only thing outside Git.** Customer
   identity/profile (name, email, org tag) and the requester↔ticket link live in a
   small **erasable directory** (deletable rows). Git tickets reference an
   **opaque requester id**, never an email/name in frontmatter.
2. **Erasure = anonymization.** A DSAR erasure deletes the identity record →
   the opaque requester id in Git becomes unresolvable. Same model as JSM, on
   infrastructure we control.
3. **Ticket bodies stay in Git, cleartext by default.** They are **encrypted**
   when either (a) sensitivity/compliance-tagged, or (b) **born encrypted** — the
   creator chose "encrypt" at create time (the encrypt button). Encryption uses a
   **per-requester key**; erasure additionally **crypto-shreds** it. Encrypt is a
   create-time decision and is **not retroactive** over Git history.
4. **Residual free-text PII** in untagged cleartext bodies is handled by manual
   redaction, with history-rewrite as the rare heavy escape hatch — explicitly
   **Atlassian-parity**, and documented as a bound rather than hidden.
5. **Bounded-by-substrate principle.** Scree provides no stronger confidentiality/
   integrity/erasure guarantee than GitLab plus this selective encryption.

### Consequences

- Good: routine erasure is a row delete (anonymization); privacy-conscious or
  sensitive tickets get crypto-shred; only a tiny identity directory leaves Git;
  honest, incumbent-parity posture.
- Bad / accepted: untagged cleartext body PII isn't auto-erasable (manual/rare
  rewrite); the identity directory is a second store to operate and protect;
  encrypted tickets are metadata-only in the index (not full-text searchable).
- F-01: cleartext tickets are kept private by **constraining the desk repo to
  agents + Gateway-only** for non-agents; born-encrypted/tagged tickets are
  additionally unreadable by clone.

## Open follow-up (architect)

- Identity-directory store choice (GitLab DB-adjacent vs separate) and its backup/
  residency handling (relates to OQ-X-007/008).
- Encryption tooling for per-requester keys (OQ-X-009).
