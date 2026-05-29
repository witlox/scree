# Agent Console (for support agents and desk leads)

The console is the internal counterpart to the customer portal. Agents work the
ticket queue; desk leads and the DPO handle review and compliance tasks. Access is
gated by your role — non-agents get a clear "not allowed" notice rather than a
half-working screen.

## Work the queue

- **Transition a ticket** through its lifecycle: `open → resolved → closed`, with a
  reopen path (`closed → open`, `resolved → open`). Illegal jumps (e.g. `open →
  closed`) are refused. Only an agent or the ticket's assignee may transition it.
- **Reply** to the customer; replies and attachments are participant-only.
- An **encrypted** (sensitive) ticket is decrypted for you on the fly by the
  gateway — the body is ciphertext at rest. Encryption is a *create-time* choice;
  you can't retroactively encrypt a ticket whose cleartext is already in history.

## Publish to the community knowledge base

To turn a resolved ticket into a public answer, **promote it to community-visible**
(with confirmation). This publishes a **curated snapshot** frozen at promotion
time — not the live thread — so later private replies never leak. Rules:

- Only **resolved** tickets can be promoted (an open ticket is refused).
- **Reopening** a published ticket re-gates it to private and discards the
  snapshot; you must re-promote (rebuilding a fresh snapshot) to publish again.
- Encrypted tickets cannot be promoted (their content must not enter the public KB).
- The promotion is recorded in the audit trail.

## Review quarantined email

Inbound email that could not be DKIM/DMARC-verified — or whose verified sender
doesn't match the ticket it quotes — is **quarantined** instead of attributed.
Review the quarantine queue and decide what's genuine. This is the anti-spoofing
boundary: a forged "reply" can't append to someone else's ticket.

## Triage orphans

The hourly batch flags **orphaned actives** for the relevant maintainers/desk
leads:

- A risk whose owner lost access to its Space.
- An open ticket whose assignee left the desk, or that's been unassigned past the
  threshold.

Orphans are **flagged, never auto-reassigned** — you decide the new owner. The
report is scoped: you see orphans for Spaces/desks you maintain.

## Erasure (DPO only)

The Data Protection Officer can fulfill a **GDPR erasure**: it deletes the
customer's identity record (so their tickets' requester id becomes unresolvable),
purges their permission tuples, scrubs their PII from the quarantine queue, and
**crypto-shreds** any encrypted bodies (the per-customer key is destroyed). Git
history is *not* rewritten — that bound is disclosed, because the substrate is Git.
Every erasure writes a durable receipt for compliance evidence.
