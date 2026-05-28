# ADR-0008: Encryption tooling — SOPS+age (client) + Vault Transit (gateway)

- Status: accepted
- Date: 2026-05-28
- Deciders: build team
- Resolves: OQ-X-009
- Context phase: architect

## Context

ADR-0005/0006 set a split key model: client-side keys for internal sensitive
content (offline-readable), Gateway-mediated per-requester keys for external
ticket bodies (crypto-shreddable). This ADR picks the tooling.

## Decision Outcome (corrected at gate-2, AR-01)

Client-side keys buy exactly one thing: reading **encrypted** content while the
online stack (GitLab/Gateway/Vault) is **down**. Only break-glass content needs
that. So the split is by **availability requirement**, not by internal/external:

- **Default — general sensitive doc spaces + ticket bodies → Vault Transit
  (Gateway-mediated).** Per-space key for sensitive doc spaces; per-requester key
  for tickets (**erasure = delete the key** = crypto-shred, INV-DP-2). The Gateway
  decrypts per authority, so this content is **web-accessible** (resolves AR-01);
  a repo clone is ciphertext. Not offline-readable. Fits DD-017.
- **Break-glass / emergency-ops / DR / SOC / infosec-restore content → SOPS with
  `age` recipients (client-side keys).** Read **offline** from a local clone by the
  incident team; `age` keys held **out-of-band** (hardware tokens / sealed
  custody), **never in Vault** — because Vault may be down. This space holds the
  Vault/Transit-key **restore runbook** itself, decoupled from what it restores
  (AR-02).

### Consequences

- Good: one mechanism (Transit) for the common case; sensitive docs render in the
  web UI; clone is ciphertext (better privacy); break-glass content survives a full
  outage with no circular dependency on Vault/Gateway.
- Bad / accepted: general encrypted content is **not** offline-readable (the
  cleartext bulk still is); break-glass `age` keys need out-of-band custody +
  rotation discipline; two mechanisms remain, but each has a sharp distinct purpose.
- The index holds plaintext only for content it is authorized to index; encrypted
  tickets are metadata-only (INV-ENC-3).

## Notes

Break-glass `age` recipients (the incident/SOC team) are provisioned and rotated
out-of-band; the recipient list lives with the break-glass content. Vault Transit
keys are tier-1 for DR (AR-02) — their loss is mass data loss.
