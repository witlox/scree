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

## Decision Outcome

- **Internal sensitive content (designated doc/risk spaces) → SOPS with `age`
  recipients.** Partial-file encryption (encrypt the body/sensitive fields, leave
  routing metadata cleartext), multiple recipients, key rotation by re-encrypting
  to a new recipient set. Authorized staff hold `age` keys locally → clone +
  decrypt + grep **offline** (satisfies INV-ENC-2 / INV-DEG-1 for key-holders).
- **External ticket bodies (tagged or born-encrypted) → Vault Transit**, one
  **key per requester**. The Gateway calls Transit encrypt/decrypt; customers
  never hold keys. **Erasure = delete the requester's Transit key** (crypto-shred,
  INV-DP-2). Fits DD-017 (Vault holds keys, not in the user auth hot path).

### Consequences

- Good: offline read preserved for staff; crypto-shred is a single key-delete;
  metadata stays cleartext so routing/permission still work; no customer-held keys.
- Bad / accepted: two encryption mechanisms to operate; Vault Transit availability
  is on the path for encrypted-ticket read/write (Vault down → those degrade,
  FM-6); SOPS recipient management is an ops task (rotation = re-encrypt).
- The search index holds plaintext only for content it is authorized to index;
  encrypted tickets are metadata-only (INV-ENC-3).

## Notes

age keys for staff are provisioned/rotated out of band (recipient list in the
repo). A future option is Vault-issued age identities; not required for v1.
