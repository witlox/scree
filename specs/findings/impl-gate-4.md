# Implementation Gate 4 — Adversary Findings

Adversarial pass over the inbound email ingestion slice merged in PR #56
(`integration/o365/inbound.py`, `servicedesk/email_routing.py`,
`servicedesk/service.py:ingest_email`, `servicedesk/comments.py`, Gateway
`POST /tickets/inbound-email`). Primary target: the email pipeline attack surface
(verification/threading spoofing, attribution) and INV-EMAIL-1 / INV-DP-1.

Project policy: **all findings are fixed before phase graduation** — severity
sets order, not whether.

---

## Finding G4-01: Attacker-supplied `Authentication-Results` is trusted → INV-EMAIL-1 verification bypass
- **Severity:** High
- **Category:** Security > integration trust boundary / input validation
- **Location:** `api/scree/integration/o365/inbound.py:28-32` (`_dmarc_pass`)
- **Spec reference:** INV-EMAIL-1 (verified before use); integration-contracts (trust the ingress MTA, not the message)
- **Description:** `_dmarc_pass` joins **every** `Authentication-Results` header in
  the message and returns true if the substring `dmarc=pass` appears anywhere. The
  raw message is fully attacker-controlled, and a relaying MTA leaves any
  pre-existing `Authentication-Results` headers in place. So an attacker simply
  includes their own `Authentication-Results: ...; dmarc=pass` header. There is no
  check that the header was added by our trusted ingress MTA (no authserv-id /
  top-most-header rule) and no check that the verdict's `header.from=` matches the
  `From` we parse. Combined with a spoofed `From:` equal to a victim's requester,
  this lets an attacker forge `verified=True` and append to / be attributed on a
  victim's ticket — the exact bypass INV-EMAIL-1 exists to prevent.
- **Evidence:**
  ```
  From: r.okafor@uni.example.ac
  Subject: Re: [SCREE-123] gimme the data
  References: <CA+abc123@mail.uni.example.ac>
  Authentication-Results: mx.scree; dmarc=pass   <-- forged by attacker
  ```
  `verified=True`, `from_addr == requester` → routed to **append** on the victim's ticket.
- **Suggested resolution:** Trust only the `Authentication-Results` header(s) added
  by our own authserv-id (the top-most, set by the ingress MTA), discard the rest;
  parse the structured verdict (not a substring) and require `dmarc=pass` **with
  `header.from` aligned to the `From` address actually used**. Better: don't carry
  the verdict in-band at all — have the trusted poller/MTA pass a separate,
  trustworthy "verified" signal to the Gateway.

## Finding G4-02: New-ticket path requires no verification → spoofable requester attribution
- **Severity:** Medium
- **Category:** Security > authorization / identity binding
- **Location:** `api/scree/servicedesk/service.py:70-84` (`ingest_email` new branch); `servicedesk/email_routing.py:route_inbound`
- **Spec reference:** INV-EMAIL-1 ("inbound email is verified before use"); INV-DP-1
- **Description:** `route_inbound` only quarantines on a *candidate match*; an
  unverified email with no threading match falls through to `new`, and
  `ingest_email` creates a ticket with `requester = ext:<from_addr>` and grants
  that id the `requester` viewer relation — **without checking `email.verified`**.
  An attacker can therefore open tickets attributed to any spoofed sender address
  and seed viewer-relation tuples for arbitrary `ext:` ids. INV-EMAIL-1 says
  inbound email is verified *before use*, not only before threading.
- **Evidence:** unverified mail `From: vip@victim.example`, subject "help" → a new
  ticket with `requester=ext:vip@victim.example` and a viewer grant for it.
- **Suggested resolution:** Require `verified` before attributing a requester:
  unverified mail with no match should be quarantined (or created as an
  unattributed/unverified intake that an agent triages), never granted a requester
  relation on a spoofable address.

## Finding G4-03: Requester id minted directly from the email address → PII in Git/OpenFGA (INV-DP-1)
- **Severity:** Medium
- **Category:** Security/Privacy > data protection
- **Location:** `api/scree/servicedesk/email_routing.py:requester_of`; used by `ingest_email`
- **Spec reference:** INV-DP-1 (opaque requester; external-customer PII lives in the erasable identity directory, **out of Git**); module-graph `access/` identity directory
- **Description:** `requester_of(email) = f"ext:{email.from_addr}"` embeds the raw
  email address (PII) into the requester id, which becomes the ticket's
  `requester` (persisted to Git) and the subject of OpenFGA tuples. INV-DP-1
  requires the requester to be an **opaque** id, with the email↔id mapping held in
  the erasable identity directory outside Git — precisely so GDPR erasure
  (crypto-shred/anonymise) is possible. Embedding the address defeats erasability
  and leaks PII into the Git substrate and the authz store.
- **Evidence:** a ticket created from email carries `requester="ext:alice@x.ac"`;
  erasing Alice would require rewriting Git history and OpenFGA tuples.
- **Suggested resolution:** Resolve the sender to an opaque id via the identity
  directory (`access/`), store only that id on the ticket/tuples, and keep the
  email in the erasable directory. (The analyst's illustrative `ext:<addr>` ids
  should be read as placeholders for the opaque directory id.)

## Finding G4-04: Generated `email_token` is hex but the matcher accepts only digits → token threading is dead for real tickets
- **Severity:** Medium
- **Category:** Correctness > semantic drift
- **Location:** `api/scree/servicedesk/service.py:62` (`email_token=f"SCREE-{tid.split('-')[1]}"`) vs `servicedesk/email_routing.py:_TOKEN` (`\[(SCREE-\d+)\]`)
- **Spec reference:** ticket_origins.feature ("Email reply missing headers threads via the [SCREE-NNN] token")
- **Description:** New email tickets get `email_token = "SCREE-" + uuid.hex[:8]`,
  whose suffix can contain `a-f`. `extract_token` matches `SCREE-\d+` (digits
  only), so a reply quoting an adapter-generated token (e.g. `[SCREE-3f9ab2c1]`)
  never matches. Header threading still works, but the **token fallback — the
  whole point of which is replies whose RFC headers were stripped — is dead for
  every ticket the adapter actually creates.** It only "works" for manually-seeded
  numeric tokens (as in the tests), masking the bug.
- **Evidence:** create an email ticket → token `SCREE-3f9ab2c1`; a header-less
  reply with subject `Re: [SCREE-3f9ab2c1] ...` → `extract_token` returns None → new
  duplicate ticket instead of threading.
- **Suggested resolution:** Make the token format and the matcher agree — use a
  numeric sequence (`SCREE-<n>`, matching `\d+` and the spec's `[SCREE-NNN]`), or
  widen the regex to the actual token charset. Prefer a stable numeric ticket
  number, which is also what customers expect to quote.

## Finding G4-05: Quarantine outcome is not persisted — "held for agent review" is unimplemented
- **Severity:** Medium
- **Category:** Robustness > degradation correctness / spec compliance
- **Location:** `api/scree/servicedesk/service.py:75-78` (`ingest_email` quarantine branch)
- **Spec reference:** INV-EMAIL-1 ("quarantined **for agent review**"); ticket_origins.feature spoof scenario
- **Description:** The quarantine branch returns `{"action":"quarantine", ...}` but
  stores nothing — no quarantine queue, no record, no agent-review surface. The
  suspicious email is effectively dropped; only the poller sees a transient
  response. INV-EMAIL-1 and the feature explicitly require the mail be **held for
  agent review**, which is not implemented, so genuine misdirected replies (and
  attack attempts) silently vanish.
- **Evidence:** a quarantined email leaves no trace in any store; an agent has
  nothing to review.
- **Suggested resolution:** Persist quarantined emails to a review queue/store
  (with reason + raw message) and expose an agent endpoint to review/release them.

## Finding G4-06: No size bound on the inbound raw email → resource exhaustion
- **Severity:** Medium
- **Category:** Robustness > resource exhaustion
- **Location:** Gateway `POST /tickets/inbound-email` (`raw: str = Body(...)`); `parse_inbound`
- **Spec reference:** failure-modes (bound external input); cf. G2-07 (doc content cap)
- **Description:** The doc-write path was capped at 1MB (G2-07), but the inbound
  email `raw` body has no size limit and `parse_inbound`/`msg.walk()` materialise
  the whole message and walk every MIME part. A very large or deeply-multipart
  email is an unbounded memory/CPU sink on the single enforcement point.
- **Evidence:** `POST /tickets/inbound-email {"raw": "<100MB message>"}` is parsed
  in full.
- **Suggested resolution:** Cap the accepted `raw` size and bound MIME part
  count/nesting before parsing, returning 413/422 past the limit.

## Finding G4-07: O(n) ticket scan per inbound email (no index)
- **Severity:** Low
- **Category:** Robustness > performance
- **Location:** `api/scree/servicedesk/email_routing.py:_candidate` (iterates `tickets` up to twice)
- **Spec reference:** indexer-design (threading/lookup should be index-backed)
- **Description:** `_candidate` linearly scans all tickets (by Message-ID, then by
  token) on every inbound email. At scale this is O(n) per message; threading
  lookups should be index-backed (Message-ID / token → ticket) per indexer-design.
- **Evidence:** with N tickets, each inbound email scans up to 2N entries.
- **Suggested resolution:** Index tickets by `email_message_id` and `email_token`
  for O(1) threading lookups.

---

## Summary

| ID | Sev | Category | Finding |
|---|---|---|---|
| G4-01 | **High** | Security/trust-boundary | Attacker-supplied Authentication-Results trusted → INV-EMAIL-1 bypass |
| G4-02 | Medium | Security/authz | New-ticket path needs no verification → spoofable requester attribution |
| G4-03 | Medium | Privacy/data-protection | Requester id minted from raw email address → PII in Git/OpenFGA (INV-DP-1) |
| G4-04 | Medium | Correctness | Generated email_token (hex) vs matcher (`\d+`) → token threading dead for real tickets |
| G4-05 | Medium | Robustness/degradation | Quarantine not persisted — "agent review" unimplemented |
| G4-06 | Medium | Robustness/exhaustion | No size bound on inbound raw email |
| G4-07 | Low | Robustness/performance | O(n) ticket scan per inbound email |

**Counts:** 1 high · 5 medium · 1 low — **7 total.**

**Highest-risk area:** verification (G4-01 + G4-02) — the adapter trusts an
in-band, attacker-controllable verdict and skips verification entirely on the
new-ticket path, so INV-EMAIL-1 is bypassable both ways. G4-01 is `gate:blocking`.

**Resolution (2026-05-28) — all 7 resolved (PR #57):**
- G4-01 — the DKIM/DMARC verdict + aligned `sender` are now supplied out-of-band
  by the trusted poller to `POST /tickets/inbound-email`; `parse_inbound` is
  structural only and never consults `Authentication-Results`. The attacker can no
  longer forge the verdict via a message header.
- G4-02 — `route()` quarantines any unverified sender (match or not); nothing is
  attributed or threaded without a verified sender.
- G4-03 — `access/IdentityDirectory` maps the email to a stable OPAQUE id; only
  that id is stored on tickets/OpenFGA, the email stays in the erasable directory.
- G4-04 — email tickets get a numeric `SCREE-<n>` token that the `\d+` matcher
  actually matches; token-fallback threading works for real tickets.
- G4-05 — quarantined mail is persisted to a `QuarantineStore` and exposed via an
  agent-only `GET /tickets/quarantine` review endpoint.
- G4-06 — inbound `raw` is capped at 1MB (→413).
- G4-07 — threading lookups are store-indexed by Message-ID and token (O(1)).
