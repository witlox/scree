# Implementation Gate 6 — Adversary Findings

Adversarial pass over the Slack `:ticket:` capture slice merged in PR #60
(`integration/slack/capture.py`, `servicedesk/service.py:capture_from_slack`/
`link_from_slack`, Gateway `/slack/capture` + `/slack/link-ticket`). Primary
target per the profile: Slack identity-mapping failure, emoji/slash spoofing,
event authenticity, public-thread→private default.

Project policy: **all findings are fixed before phase graduation** — severity
sets order, not whether.

---

## Finding G6-01: Slack-mapped requester may be a PII-bearing id, re-introducing G4-03 on the Slack path
- **Severity:** Medium
- **Category:** Security/Privacy > data protection (INV-DP-1)
- **Location:** `api/scree/servicedesk/service.py` (`capture_from_slack`: `requester = slack_dir.resolve(author)`); `integration/slack/capture.py:SlackDirectory`
- **Spec reference:** INV-DP-1 (opaque requester; PII out of Git); G4-03 resolution (email path mints an opaque id)
- **Description:** The email path was fixed (G4-03) to resolve the sender to an
  **opaque** id via `IdentityDirectory` so no PII enters Git/OpenFGA. The Slack
  path instead stores whatever `SlackDirectory.resolve` returns directly as the
  ticket `requester` and OpenFGA tuple subject. Per the feature the mapped value is
  `ext:r.okafor@uni.example.ac` — which embeds the email address (PII). So a
  Slack-captured ticket re-introduces exactly the leak G4-03 closed, and the two
  ingestion paths are inconsistent (opaque vs PII-bearing requester).
- **Evidence:** `SlackDirectory({"U_OKAFOR": "ext:r.okafor@uni.example.ac"})` →
  captured ticket `requester="ext:r.okafor@uni.example.ac"` persisted to the store
  and granted in OpenFGA.
- **Suggested resolution:** Resolve the Slack-mapped customer to the same opaque
  principal the rest of the system uses (Keycloak `sub` / `IdentityDirectory`),
  not an email-bearing string; keep any email in the erasable directory. Make the
  requester opaque regardless of what the raw mapping value looks like.

## Finding G6-02: Slack capture trusts arbitrary event fields from any agent — no event authenticity, over-broad authz
- **Severity:** Medium
- **Category:** Security > integration trust boundary / authorization
- **Location:** Gateway `/slack/capture` + `/slack/link-ticket` (`if not ticket_authority.is_agent(principal)`); `capture_from_slack` (trusts `reactor`/`author` from the body)
- **Spec reference:** module-graph DD-006 (adapters are clients; webhook authenticity, signed); INV-SLACK-1; cf. G2-02 / G4-01
- **Description:** The endpoints accept `{reactor, author, snapshot}` and trust them
  wholesale, gated only on `is_agent` — i.e. **any** agent (every human support
  agent, not just the Slack bot service account) can POST a forged capture
  attributing a requester-private ticket to an arbitrary mapped customer, or forge
  a `/link-ticket`. There is no binding to a genuine, signed Slack event (the
  Slack signing-secret check lives only in the bot, with nothing tying the gateway
  call back to it) and no dedicated bot/service principal distinct from agents.
  This is the Slack analogue of G4-01 (out-of-band trust) and G2-02 (forgeable
  attribution). The same over-broad `is_agent` gate also applies to the email
  inbound endpoint.
- **Evidence:** any agent token → `POST /slack/capture {"reactor":"U_AGENT","author":"U_OKAFOR"}`
  mints a ticket attributed to Okafor; nothing proves a real Slack reaction occurred.
- **Suggested resolution:** Restrict ingestion endpoints (`/slack/*`, `/tickets/inbound-email`)
  to a dedicated **service principal** (the bot/poller), separate from human agents;
  carry a verifiable signal of event authenticity (e.g. the bot forwards/has
  validated the Slack signature, and the gateway requires the service principal).

## Finding G6-03: Rate limiter is per-process, unbounded, and counts attempts not captures
- **Severity:** Low
- **Category:** Robustness > resource/correctness
- **Location:** `api/scree/integration/slack/capture.py:CaptureRateLimiter`
- **Spec reference:** INV-SLACK-1 (rate-limited per Slack user to prevent spam/DoS); slack_capture.feature ("created 5 captures")
- **Description:** Three smaller issues: (1) the limiter is in-memory per process, so
  with multiple gateway replicas a user gets `limit × replicas` captures — the
  anti-DoS guarantee doesn't hold horizontally. (2) `_hits` grows without bound (one
  list per distinct Slack user, never evicted). (3) `allow()` is called before
  author resolution, so it counts **attempts**, including refusals — diverging from
  the spec's "5 captures" (successes) and letting failed attempts burn a user's budget.
- **Evidence:** two gateway processes each allow 5 → 10 captures; reacting to
  unmappable-author messages consumes slots without creating tickets.
- **Suggested resolution:** Back the limiter with shared state (e.g. Redis) for the
  real deploy (note as the scaling path); evict idle users / cap the map; and count
  successful captures (or document that attempts are counted deliberately for DoS).

---

## Summary

| ID | Sev | Category | Finding |
|---|---|---|---|
| G6-01 | Medium | Privacy/data-protection | Slack-mapped requester may be PII-bearing (re-introduces G4-03) |
| G6-02 | Medium | Security/trust-boundary | Slack endpoints trust arbitrary event fields from any agent; no authenticity, over-broad authz |
| G6-03 | Low | Robustness | Rate limiter per-process, unbounded, counts attempts not captures |

**Counts:** 0 critical · 0 high · 2 medium · 1 low — **3 total.** No `gate:blocking`.

**Highest-risk area:** identity/trust (G6-01 + G6-02) — the new path quietly
re-introduces PII into the requester id and trusts forgeable event fields from any
agent, undoing guarantees the email hardening established.

**Resolution (2026-05-28) — all 3 resolved (PR #61):**
- G6-01 — `TicketService._principal_for` resolves an external Slack-mapped customer
  to an OPAQUE id via the identity directory (internal agents pass through), so the
  stored requester/capturer carry no PII; link authz uses the same resolution.
- G6-02 — Slack `/slack/*` and email `/tickets/inbound-email` now require a
  dedicated `service_principals` member (the bot/poller), distinct from human
  agents and fail-closed; the bot remains the Slack-signature verification boundary.
- G6-03 — the limiter counts only resolvable captures (reordered), evicts stale
  per-user entries to bound memory, and documents the shared-state requirement for
  multi-replica deploys.
