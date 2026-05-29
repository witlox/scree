# Scree — Integration Contracts

What Scree uses from each external system, how it authenticates, and how it
behaves when the system is unavailable. Adapters are clients of the Gateway and
hold no privileged backend access (DD-006).

## GitLab (substrate)

- **Used for:** repo read/write (resources as files), commits (authorship via
  token exchange), Advanced Search, webhooks, branch protection + CODEOWNERS
  (INV-GOV-1), group/project membership (coarse authority).
- **Auth:** per-user OIDC token exchanged (RFC 8693) for a GitLab-scoped token;
  external-customer writes via the desk service account (INV-ID-4).
- **Failure:** unreachable → local-clone reads succeed; writes refused, not queued
  (INV-DEG-1). Advanced Search down → aggregation falls back to the index with an
  `as-of` marker.

## Keycloak (identity)

- **Used for:** OIDC authentication (internal + external realms), token exchange.
- **Auth:** standard OIDC; Gateway validates tokens; Vault not required for user auth.
- **Failure:** unreachable → no new logins; valid tokens honored to expiry (FM-3).

## OpenFGA (ticket ReBAC)

- **Used for:** `Check(user, relation, ticket)` and `ListObjects(user, "read",
  ticket)` — the latter powers the aggregation filter (INV-AGG). Tuples written by
  the Gateway on ticket relation changes.
- **Auth:** service credential from Vault.
- **Failure:** unreachable → ticket authorization **fails closed** (INV-ACC-5); the
  Gateway denies rather than guesses.
- **Source of truth = Git (AR-03).** Ticket relations are authored in the ticket
  **frontmatter**; OpenFGA tuples are a **derived, rebuildable projection**
  (INV-ST-2). The Gateway commits Git **first**, then upserts tuples; if the tuple
  write fails, the next reconcile pass rebuilds it from Git (no "Git-committed but
  authority-lost" state). A reconciler periodically rebuilds tuples from Git.

## Vault (secrets + Transit)

- **Used for:** service credentials, signing keys, and **Transit** per-requester
  ticket encryption keys (ADR-0008). Erasure deletes the requester's Transit key
  (crypto-shred, INV-DP-2).
- **Auth:** Scree service identity.
- **Failure:** not in the user auth path; cached creds within TTL; encrypted-ticket
  read/write degrades while Vault is down (FM-6).

## O365 / Microsoft Graph (email)

- **Used for:** inbound mail (poll/webhook) → ticket; outbound notifications.
- **Inbound contract:** verify DKIM/DMARC; parse MIME; thread by Message-ID/
  References with `[SCREE-NNN]` token as a low-trust candidate; append only on
  verified sender match, else quarantine (INV-EMAIL-1).
- **Auth:** Graph service principal (cert-based), creds in Vault.
- **Failure:** unreachable → inbound ticket creation fails visibly; outbound retried
  with backoff (FM-2).

## Slack (chat)

- **Used for:** emoji→draft ticket, slash-link snapshot, outbound notifications;
  one public community channel.
- **Contract:** resolve Slack→Keycloak (refuse if unmapped, INV-ID-2); author =
  requester, capturer recorded; rate-limited (INV-SLACK-1); snapshot-only (DD-012).
- **Auth:** Slack app token; verify request signatures.
- **Failure:** unreachable → capture unavailable; other origins unaffected (FM-7/8).

## Attachments (Git LFS default; object storage alternative)

- **DD-002 (revised):** attachments default to **Git LFS** on the ticket repo
  (`tickets/<id>/attachments/`), so the service-desk record is uniform with the
  ticket/comment store. **S3-compatible object storage** is the configurable
  alternative (`SCREE_ATTACHMENTS_DIR`). On a born-encrypted ticket the attachment is
  stored as per-requester ciphertext, so a GDPR crypto-shred erases it (INV-DP-2),
  which is what makes Git-LFS (permanent history) acceptable for sensitive uploads.
- **Failure:** ticket text still created; attachment upload retried; failure surfaced
  to the requester (FM-14).

## OpenTelemetry (observability)

- **Used for:** traces/metrics/logs across the Gateway→downstream chain; context
  propagated through token exchange so a request is traceable end-to-end (DD-020).
