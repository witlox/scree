# Implementation Gate 9 — Adversary Findings

Adversarial pass over the token-exchange + composed-authority slice merged in PR
#66 (`access/token_exchange.py`, `access/gitlab.py`, Gateway `get_principal`
exchange + `_readable_spaces`/`_readable_groups`). Primary target: the new
per-request authority-resolution path (perf, config safety, completeness).

Project policy: **all findings are fixed before phase graduation** — severity
sets order, not whether.

---

## Finding G9-01: Token-exchange + GitLab membership resolved on every request, no caching
- **Severity:** Medium
- **Category:** Robustness > performance / load amplification
- **Location:** Gateway `get_principal` (exchange per request) + `_readable_spaces`/`_readable_groups` (resolve per request)
- **Spec reference:** indexer-design AR-08 ("resolve the requester's readable Spaces ONCE (cached, short TTL) — never a GitLab API call per item")
- **Description:** With the composed authority configured, every authenticated
  request performs (a) a Keycloak token-exchange round-trip and (b) a paginated
  GitLab membership lookup. Resolution is cached for the duration of a single
  request (good), but **not across requests** — AR-08 calls for a short-TTL cache.
  So a busy Gateway hammers Keycloak and GitLab once per request each, adding
  latency and a load-amplification/DoS surface (one client request → ≥2 upstream calls).
- **Evidence:** N client requests → N token-exchanges + N membership lookups, even
  for the same user within seconds.
- **Suggested resolution:** Short-TTL cache (keyed by subject token / GitLab token)
  for both the exchanged token and the resolved readable sets, per AR-08; accept the
  bounded staleness window the TTL implies.

## Finding G9-02: Partial composed-authority config silently yields empty authority
- **Severity:** Medium
- **Category:** Robustness > degradation correctness (fail-loud)
- **Location:** Gateway `create_app` / `_readable_spaces` (`token = getattr(request.state, "gitlab_token", None); ... if token else set()`)
- **Spec reference:** cf. G3-03 / G8-01 fail-closed-loud pattern
- **Description:** If `gitlab_authority` is configured but no token source is wired
  (`token_exchanger` absent and not the dev header path), then no `gitlab_token` is
  ever set, `readable_spaces` resolves to the empty set, and **every** bearer
  request sees nothing — docs/risks/planning all empty. It fails *closed* (safe) but
  *silently*: the app looks broken rather than reporting a misconfiguration, the same
  trap G3-03 (planning) and G8-01 (crypto) now guard against.
- **Evidence:** `create_app(..., authenticator=X, gitlab_authority=Y)` with no
  `token_exchanger` → all authorized reads return empty.
- **Suggested resolution:** Fail loud at startup — require a token source when
  `gitlab_authority` is set (token_exchanger, or the dev header opt-in).

## Finding G9-03: readable_spaces counts only membership, missing visibility-based read access
- **Severity:** Low
- **Category:** Correctness > authority completeness
- **Location:** `api/scree/access/gitlab.py:GitLabAuthority.readable_spaces` (`membership=true`)
- **Spec reference:** INV-ACC-2 (GitLab read access)
- **Description:** Readable Spaces are resolved via `membership=true`, so a Space the
  user can read by **visibility** (public/internal project they're not an explicit
  member of) is omitted — an under-grant. For Scree's private org Spaces this matches
  the intended model, but it diverges from "can read in GitLab" for any non-private
  Space.
- **Evidence:** a user who can view a public/internal project but isn't a member
  doesn't get it in `readable_spaces`.
- **Suggested resolution:** Either accept membership as the Space-access model
  (document it: Spaces are member-access private projects, INV-ACC-2) or include
  visibility-readable projects. Decide deliberately.

---

## Summary

| ID | Sev | Category | Finding |
|---|---|---|---|
| G9-01 | Medium | Robustness/performance | Token-exchange + membership resolved every request, no cross-request cache (AR-08) |
| G9-02 | Medium | Robustness/fail-loud | Partial composed-authority config silently yields empty authority |
| G9-03 | Low | Correctness | readable_spaces counts only membership (under-grant for public Spaces) |

**Counts:** 0 critical · 0 high · 2 medium · 1 low — **3 total.** No `gate:blocking`.

**Highest-risk area:** the per-request resolution path — uncached upstream calls
(G9-01) and a silent-empty misconfig (G9-02).
