# Frontend Gate 1 — Adversary Findings

First adversarial pass over the `web/` frontend built this cycle: foundation
(island mount, API client, query), auth (#108), design system (#105/#106), and the
four surfaces — knowledge (#101), portfolio/risk (#104), admin/agent (#103), portal
(#102). Lens: correctness, security, robustness at the seams. Component tests mock
`fetch` and the auth hook, so these are the kinds of defects those green tests do
**not** catch — most surface only against a live gateway + Keycloak (the
already-flagged unverified path).

Project policy: **all findings are fixed before phase graduation** — severity sets
order, not whether.

---

## Finding FE-01: Auth token race — first requests after login carry no bearer
- **Severity:** High
- **Category:** Correctness / security (auth, INV-ID-1/INV-ID-3)
- **Location:** `web/src/auth/AuthGate.tsx:18-20` (token set in `useEffect`) vs `:38` (children rendered)
- **Description:** `Gate` renders `children` as soon as `auth.isAuthenticated`, but
  writes the access token to `tokenStore` in a `useEffect`. React runs effects
  bottom-up: a surface's TanStack Query mount effect (which fires the first fetch)
  runs **before** `Gate`'s token-sync effect. So the initial requests after login go
  out with `tokenStore.get() === null` → `ApiClient` attaches no `Authorization` (and
  `devUser` is undefined in prod) → the gateway returns 401. The global `retry: 1`
  partially masks it (the retry runs after the token lands), but every surface load
  emits a spurious **unauthenticated** request — audited by the gateway as a
  principal-less 401 (pollutes the INV-ID-3 trail) — and any non-retried request
  (a user mutation fired in that window, or if retry is disabled) fails outright.
- **Evidence:** `client.ts:51-53` — no token and no devUser ⇒ no auth header. Effect
  ordering makes the first fetch precede `tokenStore.set`.
- **Suggested resolution:** Set the token **before** rendering children — e.g. write
  `tokenStore` synchronously in render when authenticated, or don't render children
  until the token is in the store. Then the first fetch is authenticated.

## Finding FE-02: OIDC redirect_uri is the live pathname, not a fixed callback
- **Severity:** Medium
- **Category:** Security / robustness (auth config)
- **Location:** `web/src/auth/AuthProvider.tsx:17`
- **Description:** `redirect_uri = origin + window.location.pathname`. Keycloak
  validates the redirect against the client's registered URIs. With surfaces served
  at different paths (`/docs`, `/portal`, `/admin`, …), each path must be registered
  or login fails with "Invalid redirect_uri"; a single registered callback is the
  norm. The dynamic, partly user-influenceable pathname is also an open-redirect
  vector if the client is ever registered with a wildcard.
- **Evidence:** any surface not at the exact registered path → IdP rejects the round-trip.
- **Suggested resolution:** Use one fixed `redirect_uri` (e.g. `origin + "/auth/callback"`)
  registered once; restore the originating location from app state after callback.

## Finding FE-03: DocEditor silently saves the stale body if the editor didn't initialize
- **Severity:** Medium
- **Category:** Correctness (data loss)
- **Location:** `web/src/features/docs/DocEditor.tsx` (save `mutationFn`: `editorApi.current ? getMarkdown() : initial.body`)
- **Description:** The TipTap editor is lazy-loaded and exposes its API via `onReady`.
  If that chunk fails to load (network/CSP) or `onReady` hasn't fired, `editorApi.current`
  is null and Save falls back to `initial.body` — committing the **unedited** content
  as if it were a successful save. A user who typed into a not-yet-ready editor loses
  their edits with no error.
- **Evidence:** the `? : initial.body` fallback masks an uninitialized editor as a no-op save.
- **Suggested resolution:** Disable Save until `editorApi.current` is set (editor ready),
  or refuse to save and surface an error when it is null — never silently substitute
  the original body.

## Finding FE-04: No global 401 handling — expired sessions look like generic load errors
- **Severity:** Medium
- **Category:** Robustness (auth lifecycle)
- **Location:** `web/src/api/client.ts:56-64`; query error rendering across features
- **Description:** A 401 throws a generic `ApiError`; every view renders it as
  "Couldn't load …". `automaticSilentRenew` refreshes proactively, but a revoked or
  hard-expired session (or the FE-01 window) yields a dead-end error instead of a
  re-authentication. There is no interceptor mapping 401 → `signinRedirect`.
- **Suggested resolution:** Centralize: on `ApiError(401)`, trigger re-auth
  (`signinRedirect`) / clear the session, rather than surfacing a generic error.

## Finding FE-05: Unguarded `JSON.parse` of `data-props` aborts all island mounts
- **Severity:** Low
- **Category:** Robustness
- **Location:** `web/src/app/mountIslands.tsx:29-31`
- **Description:** `JSON.parse(el.dataset.props)` is unguarded inside the
  `querySelectorAll(...).forEach`. One malformed `data-props` attribute throws, the
  exception propagates out of `forEach`, and **no further islands on the page mount**.
  Props come from trusted server HTML today, but one bad attribute breaks the whole page.
- **Suggested resolution:** `try/catch` the parse per element; warn and skip on failure.

## Finding FE-06: No error boundary around islands — a render error blanks the surface
- **Severity:** Low
- **Category:** Robustness
- **Location:** `web/src/app/mountIslands.tsx:32-42`
- **Description:** Each island root renders the feature directly. An unhandled render
  error unmounts the React tree, leaving an empty island with no fallback or report.
- **Suggested resolution:** Wrap each island in an error boundary that renders a
  fallback (and could report).

## Finding FE-07: MarkdownView relies on DOMPurify defaults
- **Severity:** Low
- **Category:** Security (defense-in-depth)
- **Location:** `web/src/features/docs/MarkdownView.tsx:9-13`
- **Description:** `DOMPurify.sanitize(marked.parse(...))` is the correct shape and
  blocks script/handler/`javascript:` injection. But it leans on the default profile;
  it does not explicitly forbid risky embeds (`iframe`/`object`/`embed`/`form`) or add
  `rel="noopener noreferrer"` to links. Doc bodies are authored by space-writers
  (semi-trusted) and rendered to all readers of the shared KB.
- **Suggested resolution:** Pin an explicit allowlist / `FORBID_TAGS`, add a link hook
  for `rel`/`target`, and consider Trusted Types.

## Finding FE-08: `columns` recreated every render in the admin ticket queue
- **Severity:** Low
- **Category:** Robustness / performance
- **Location:** `web/src/features/admin/AdminApp.tsx` (TicketQueue `columns`)
- **Description:** The column defs are built in the component body (closure over the
  transition mutation), so a new array identity is passed to `useReactTable` on every
  render — unnecessary churn and a footgun for column-keyed table state. (Portfolio/risk
  columns are module-level and fine.)
- **Suggested resolution:** `useMemo` the columns (or hoist + inject the mutation via a cell context).

## Finding FE-09: Community KB search results are not actionable
- **Severity:** Low
- **Category:** Correctness / UX
- **Location:** `web/src/features/portal/CustomerPortal.tsx` (CommunityHelp); `web/src/features/portfolio` (n/a)
- **Description:** `/community/search` returns bare ticket ids; the portal renders them
  as a plain list with no way to open the community-visible ticket. A dead-end result
  set — the customer sees ids they can't act on. (The community snapshot is readable,
  so a link into the detail view is feasible.)
- **Suggested resolution:** Link each hit to its community ticket view (or render the
  snapshot title/excerpt the gateway could provide).

## Finding FE-10: No request timeout/abort
- **Severity:** Low
- **Category:** Robustness
- **Location:** `web/src/api/client.ts:55` (`fetch` with no `AbortSignal`)
- **Description:** Requests have no timeout; a hung gateway leaves queries pending
  indefinitely (TanStack Query has no default timeout). No cancellation on unmount/route
  change either.
- **Suggested resolution:** Attach an `AbortSignal` with a timeout (and wire query
  cancellation) in the client.

---

## Accepted / noted (not findings)
- **Token storage:** access token in `tokenStore` (memory) + oidc-client-ts session in
  `sessionStorage` is the standard SPA OIDC trade-off; XSS exposure is mitigated by the
  sanitizer (FE-07) and a deploy-time CSP (server concern, not frontend code).
- **Dev-header `?as=` path:** dev-only (`import.meta.env.DEV`) and requires the gateway's
  `allow_insecure_header_auth`; not present in production builds.

## Summary

| ID | Sev | Category | Finding |
|---|---|---|---|
| FE-01 | **High** | Correctness/security (auth) | First post-login requests carry no bearer (token set in effect after children render) → spurious 401s |
| FE-02 | Medium | Security/robustness (auth) | redirect_uri is the live pathname, not a fixed registered callback |
| FE-03 | Medium | Correctness (data loss) | DocEditor saves stale `initial.body` if the lazy editor never initialized |
| FE-04 | Medium | Robustness (auth) | No global 401 → re-auth; expired sessions look like generic load errors |
| FE-05 | Low | Robustness | Unguarded `JSON.parse(data-props)` aborts all island mounts |
| FE-06 | Low | Robustness | No error boundary around islands |
| FE-07 | Low | Security (defense-in-depth) | MarkdownView relies on DOMPurify defaults (no explicit forbid/rel) |
| FE-08 | Low | Robustness/perf | Admin ticket-queue `columns` recreated each render |
| FE-09 | Low | Correctness/UX | Community KB search results aren't actionable (bare ids) |
| FE-10 | Low | Robustness | No request timeout/abort in the API client |

**Counts:** 0 critical · 1 high · 3 medium · 6 low — **10 total.**

**Highest-risk area:** the auth seam — FE-01 (token race) emits unauthenticated,
audited 401s on every real-OIDC surface load and is invisible to the mocked component
tests; FE-02/FE-04 round out auth-lifecycle correctness. These only manifest against a
live gateway + Keycloak, the path that has not yet been browser-verified.
