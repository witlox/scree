# Fidelity — Frontend (`web/`)

First fidelity measurement of the frontend (the baseline index was `api/`-only).
**14 test files / 42 tests**, all green. Vite + React 19 + TS strict; vitest (jsdom).

## Depth by area

| Area | Tests | Depth | Note |
|---|---|---|---|
| API client (`api/client`) | client.test | THOROUGH | bearer attach, dev-user header, ApiError on non-2xx (mocked fetch) |
| Auth (`auth/*`) | AuthGate, config, session | THOROUGH | gate states (authenticated→children + token sync, redirect, error, dev-passthrough), env gating + fixed redirect_uri, 401 bridge |
| Island bootstrap (`app/mountIslands`) | mountIslands | THOROUGH | mount + props, unregistered-warn, empty, **malformed-props tolerated** (FE-05) |
| Design-system primitives (`ui/*`) | primitives, DataTable | THOROUGH | Button type, TextField label/aria-invalid/describedby, **Radix Dialog open+Escape**, **TanStack Table sort + aria-sort** (real libs) |
| Editor round-trip (`editor/markdown`) | markdown | THOROUGH | real TipTap markdown round-trip |
| Markdown render (`docs/MarkdownView`) | MarkdownView | THOROUGH | render + **sanitization strips script/iframe/handlers/javascript:** (FE-07, security) |
| Docs surface | docs/api, DocList | THOROUGH | buildDocContent/classifyWriteError (pure), list/empty/error states |
| Portfolio/risk surface | PortfolioApp | THOROUGH | rollup totals + risks, empty, error |
| Admin/agent surface | AdminApp | THOROUGH | queue + transition (PATCH), forbidden notice, **erase confirm Dialog → DELETE** |
| Portal surface | CustomerPortal | THOROUGH | list + open, reply (POST), community KB search |

Component logic is genuinely deep (real components + faithful mocks); pure helpers and
the security-sensitive render path (sanitization) are tested directly.

## Boundary fidelity (the load-bearing gap)

| Seam | In tests | Rating |
|---|---|---|
| Frontend → Gateway (HTTP) | `fetch` mocked / routed per test | stubbed — `@api`-equivalent depth |
| Browser → Keycloak (OIDC login) | `useAuth` mocked (`react-oidc-context`) | stubbed; real auth-code+PKCE flow **never exercised** |
| End-to-end (`@e2e` Playwright) | config exists; **not run** (no browser/Keycloak) | **UNVERIFIED** |

**This is the frontend's defining gap, exactly analogous to the backend's `@contract`
tier:** the component tests mock the gateway and the auth hook, so they cannot catch
real-integration bugs. **FE-01 (the post-login token race) was precisely such a bug** —
green under mocks, broken against a real Keycloak. The Playwright `@e2e` tier (#97/G-D1)
is wired but unrun; a live browser + Keycloak + gateway pass is the top frontend gate.

## Generated types

Request/response types are **generated** from the gateway OpenAPI schema (the gateway
endpoints now carry `response_model`s); no hand-written types remain. Drift between the
client and the gateway contract cannot accumulate silently.

## Adversary posture

Frontend Gate 1 (`frontend-gate-1.md`) — 10 findings, **all resolved**: the auth seam
(FE-01 token race, FE-02 redirect_uri, FE-04 401→re-auth) plus data-loss (FE-03),
robustness (FE-05/06/10), and sanitizer hardening (FE-07). The auth seam is the
highest-risk area and the one the mocked tests are blind to.

## Confidence

**High** for component logic, design-system accessibility, and the sanitization path;
**unverified** for the real end-to-end (browser + Keycloak + gateway) — the single
outstanding frontend risk, tracked as live verification + #97.
