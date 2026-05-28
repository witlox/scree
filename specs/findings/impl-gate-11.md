# Implementation Gate 11 — Adversary Findings

Adversarial pass over the portal-backend slice merged in PR #70 (Gateway
`/community/search`, `/portal/preferences`, `/tickets/{id}/attachments`). Primary
target: the new public/community surface and external uploads.

Project policy: **all findings are fixed before phase graduation** — severity
sets order, not whether.

---

## Finding G11-01: Community KB search decrypts and exposes encrypted-ticket content to all authenticated users
- **Severity:** Medium
- **Category:** Security > confidentiality (encryption boundary)
- **Location:** Gateway `community_search` (`service.read_comments(t.id)` for any `community_visible` ticket)
- **Spec reference:** INV-LC-2 (community = curated snapshot), ADR-0005 (encryption for sensitive content)
- **Description:** `community_search` calls `read_comments`, which **decrypts**
  encrypted bodies. If an encrypted (sensitive) ticket is ever promoted to
  `community_visible`, its decrypted content becomes searchable by **any**
  authenticated principal through the public community KB — defeating the very
  encryption that marked it sensitive. Nothing prevents promoting an encrypted
  ticket, and the search doesn't exclude encrypted ones.
- **Evidence:** create an encrypted ticket, resolve + promote it, then
  `GET /community/search?q=<secret term>` as an unrelated user → the decrypted
  body matches and surfaces.
- **Suggested resolution:** Exclude encrypted tickets from community search, and
  refuse to promote an encrypted ticket to `community_visible` (encryption ⇒ not a
  candidate for the public curated snapshot).

## Finding G11-02: Attachment upload gated on can_read → any authenticated user can attach to a community ticket
- **Severity:** Medium
- **Category:** Security > authorization (abuse/spam)
- **Location:** Gateway `add_attachment` (`if ... not ticket_authority.can_read(principal, t)`)
- **Spec reference:** portal.feature (the **requester** replies with an attachment); INV-ACC
- **Description:** Upload authorization uses `can_read`, which is true for
  **everyone** on a `community_visible` ticket. So any authenticated user can attach
  arbitrary files to someone else's community ticket — a spam/abuse and
  content-injection vector (files later shown to agents/the requester). Replying
  with an attachment should be limited to the ticket's participants (requester or an
  agent), not any reader.
- **Evidence:** a random authenticated user `POST`s an attachment to a
  `community_visible` ticket → accepted.
- **Suggested resolution:** Gate upload (and listing) on participant authority
  (`can_see_identity`: requester/agent/related), not mere read.

## Finding G11-03: External attachments are neither type-restricted nor scanned
- **Severity:** Low
- **Category:** Robustness/Security > input validation
- **Location:** Gateway `add_attachment` (`portal/stores.AttachmentStore`)
- **Spec reference:** failure-modes (external input); attachment handling
- **Description:** The portal accepts attachment uploads from external customers with
  no content-type/extension restriction and no malware scanning. A hostile upload
  (e.g. an executable) is stored and later served to agents — a malware-distribution
  vector. (Also: community search is an unindexed O(n)+decrypt scan per query — a
  perf note for scale.)
- **Evidence:** `POST .../attachments {"filename":"payload.exe", ...}` is stored.
- **Suggested resolution:** Restrict to an allowlist of safe extensions (reject
  obvious executables) and wire AV scanning at the object-storage boundary (deploy
  concern); index community content for search at scale.

---

## Summary

| ID | Sev | Category | Finding |
|---|---|---|---|
| G11-01 | Medium | Security/confidentiality | Community search decrypts & exposes encrypted-ticket content |
| G11-02 | Medium | Security/authz | Attachment upload on can_read → anyone can attach to a community ticket |
| G11-03 | Low | Security/input | Attachments not type-restricted/scanned (+ unindexed search) |

**Counts:** 0 critical · 0 high · 2 medium · 1 low — **3 total.** No `gate:blocking`.

**Highest-risk area:** the public/community surface — encrypted content can leak
into the KB (G11-01) and the community-read grant over-authorizes uploads (G11-02).

**Resolution (2026-05-28) — all 3 resolved (PR #71):**
- G11-01 — community search excludes encrypted tickets, and promote_community_visible refuses encrypted tickets (sensitive content cannot enter the public KB).
- G11-02 — attachment upload/listing is participant-only (can_see_identity), not mere community read.
- G11-03 — executable/script attachment extensions are rejected (415); AV scanning + search indexing noted as deploy/scale follow-ups.
