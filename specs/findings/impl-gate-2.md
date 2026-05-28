# Implementation Gate 2 — Adversary Findings

Adversarial pass over the merged custom layer after impl-gate-1 closure and the
OIDC/Keycloak work (PRs #45–#50). Scope: `api/scree/**`. Stance: every invariant
guilty until verified against spec.

Project policy: **all findings are fixed before phase graduation** — severity
sets order, not whether.

---

## Finding G2-01: Path traversal / arbitrary file write in doc write
- **Severity:** High
- **Category:** Security > input validation (path traversal)
- **Location:** `api/scree/knowledge/git_store.py:34-49` (`write`); unguarded by `api/scree/knowledge/doc_service.py:45-62`
- **Spec reference:** INV-ST-1 (writes are commits *within the Space*); permission-enforcement-map (gateway is the only write path)
- **Description:** The doc-write `path` is taken verbatim from the request body
  (`app.py:149`) and flows through `DocService.write` into
  `GitBackedDocStore.write`, which does `target = self._root / rel_path` then
  `target.write_text(text)` **before** `git add`. Nothing rejects `..` segments
  or absolute paths. `Path("/srv/repo") / "../../../../tmp/x"` and
  `Path("/srv/repo") / "/etc/cron.d/x"` both resolve outside the repo, so an
  authenticated writer gets an arbitrary-location file write with
  attacker-controlled contents. The subsequent `git add` fails (→500) only
  *after* the file is already on disk.
- **Evidence:**
  ```
  POST /docs {"path": "../../../../etc/cron.d/pwn", "content": "---\nid: x\nkind: doc\nschema_version: 1\ntitle: t\nspace: platform/handbook\n---\n* * * * * root sh -c ..."}
  ```
  Writer needs write authority to *any one* space (the check is on frontmatter
  `space`, not the path — see G2-04), then can write anywhere the process user can.
- **Suggested resolution:** Normalize and confine: reject absolute paths and any
  path whose resolved location is not under the Space root (e.g.
  `Path(root, rel).resolve().is_relative_to(root.resolve())`), and reject `..`
  segments outright. Enforce in `DocService.write` so the gateway boundary holds.

## Finding G2-02: Ticket create trusts client-supplied `requester`, ignores the authenticated principal
- **Severity:** High
- **Category:** Security > authorization / identity binding
- **Location:** `api/scree/gateway/app.py` (`create_ticket`, ~:174-183) → `api/scree/servicedesk/service.py:31-48`
- **Spec reference:** INV-DP-1 (opaque requester), INV-ID-1 (principal is the verified identity), DD-013
- **Description:** `create_ticket` resolves a verified `principal` but then calls
  `service.create(origin, requester)` using the **body** `requester`, discarding
  `principal`. Any authenticated caller can mint a ticket attributed to an
  arbitrary requester id, and the requester `viewer` grant (`authority.grant`)
  is written for that arbitrary id — not the caller. This enables
  mis-attribution/impersonation and can grant ticket read access to an id the
  caller chooses.
- **Evidence:** `POST /tickets {"origin":"api","requester":"cust-someone-else"}`
  with caller `mallory`'s token → ticket owned by `cust-someone-else`, viewer
  tuple granted to `cust-someone-else`. Caller identity never recorded.
- **Suggested resolution:** For `api`/`web` origins, bind `requester = principal`
  (ignore/forbid a body requester). Allow an explicit on-behalf-of requester only
  for agents. Email/Slack adapters set the opaque requester server-side; the open
  API must not accept a free-form requester from non-agents.

## Finding G2-03: Authentication is default-off — header identity trusted when no authenticator is configured
- **Severity:** High
- **Category:** Security > identity (default-insecure)
- **Location:** `api/scree/gateway/app.py` (`create_app` `authenticator=None` default; `get_principal` X-Spike-User fallback)
- **Spec reference:** INV-ID-1; this is the open I-03 follow-up ("authenticator mandatory in prod")
- **Description:** `authenticator` defaults to `None`. When unset, `get_principal`
  trusts the unauthenticated `X-Spike-User` header as the principal. A deployment
  that forgets to wire an authenticator is silently wide open — identity becomes
  a spoofable header on the single enforcement point. Fail-open by omission.
- **Evidence:** `create_app(store, authority)` (no authenticator) →
  `GET /docs -H "X-Spike-User: anyone"` is accepted as `anyone`.
- **Suggested resolution:** Fail closed: require an authenticator unless an
  explicit `allow_insecure_header_auth=True` (dev/spike only) flag is passed;
  log a loud warning when the insecure path is active. Tracked as the I-03 prod
  follow-up — promote to a blocking fix before any non-spike deploy.

## Finding G2-04: Doc write authority is checked against frontmatter `space`, decoupled from the storage `path`
- **Severity:** Medium
- **Category:** Security > authorization (semantic drift)
- **Location:** `api/scree/knowledge/doc_service.py:49,61`
- **Spec reference:** DD-007 (write inherits Space membership), domain-model (Space ≙ GitLab project; path is location *within* a Space)
- **Description:** `can_write(author, meta["space"])` authorizes against the
  frontmatter-declared `space`, but the file is stored at the body `path`. The
  two are never reconciled. A user with write to space A can author a doc
  declaring `space: A` and store it at a `path` belonging to space B's
  folder/repo, so the on-disk location and the authority decision diverge.
- **Evidence:** writer for `platform/handbook` posts content with
  `space: platform/handbook` to `path: policy/secret.md` — authorized by the
  handbook membership though it lands under `policy/`.
- **Suggested resolution:** Derive the Space from the `path` (the repo/folder it
  lands in) and authorize on that; or require frontmatter `space` to be
  consistent with the path prefix and reject mismatches.

## Finding G2-05: Principal derived from mutable `preferred_username` instead of immutable `sub`
- **Severity:** Medium
- **Category:** Security > identity
- **Location:** `api/scree/access/oidc.py:48`
- **Spec reference:** INV-ID-1/2 (stable principal identity)
- **Description:** `principal = preferred_username or sub`. In Keycloak,
  `preferred_username` is mutable and can be reassigned/reused after a user is
  deleted; `sub` is the stable subject. Authority bindings keyed on a renamed or
  reused username can mis-grant (a new user inheriting an old username inherits
  its access) or orphan access on rename.
- **Evidence:** rename user `rivera`→`rivera2` in Keycloak, recreate a new
  `rivera`; the new account presents `preferred_username=rivera` and matches any
  authority keyed on `"rivera"`.
- **Suggested resolution:** Use `sub` as the authorization principal; treat
  `preferred_username` as display only. Key Authority/OpenFGA tuples on `sub`.

## Finding G2-06: community_visible ticket views leak the opaque requester id to all authenticated principals
- **Severity:** Medium
- **Category:** Security/Privacy > aggregation leak
- **Location:** `api/scree/gateway/app.py` (`list_tickets`/`get_ticket` return `requester`); reachable via `TicketAuthority` community_visible path
- **Spec reference:** INV-DP-1, INV-AGG, INV-ENC-3 (no PII/correlation handle in shared views)
- **Description:** A `community_visible` ticket is readable by any authenticated
  principal, and the response body includes `requester`. Although the requester
  id is "opaque", exposing it on every community-visible ticket lets any user
  correlate all of a requester's promoted tickets — a stable cross-ticket
  linkage that the opaque-id design was meant to prevent leaking publicly.
- **Evidence:** two promoted tickets from the same customer share the same
  `requester` value in their public responses → correlatable.
- **Suggested resolution:** Omit/blank `requester` (and any actor fields) in
  responses served under the community_visible grant; expose requester only to
  agents and the requester themself.

## Finding G2-07: Frontmatter YAML parsed with no size or alias-expansion limit (DoS)
- **Severity:** Medium
- **Category:** Robustness > resource exhaustion
- **Location:** `api/scree/knowledge/frontmatter.py:23` (`yaml.safe_load`)
- **Spec reference:** failure-modes (external input bounded); robustness vectors
- **Description:** `yaml.safe_load` is safe against code execution but **not**
  against anchor/alias expansion bombs ("billion laughs"); a small frontmatter
  block can expand to gigabytes. Frontmatter is external input (web form, email,
  Slack, migration). There is also no cap on document/frontmatter size.
- **Evidence:** nested YAML anchors (`a: &a [*a,*a,...]`) in frontmatter →
  CPU/memory blowup during `safe_load`.
- **Suggested resolution:** Enforce a max content size before parsing; disable or
  bound alias expansion (custom Loader rejecting anchors/aliases in frontmatter),
  and cap nesting depth.

## Finding G2-08: 500-level (unhandled) errors bypass the audit middleware
- **Severity:** Medium
- **Category:** Robustness > observability (audit gap)
- **Location:** `api/scree/gateway/app.py` (`audit_mw`: `response = await call_next(request)` then `audit.record(...)`)
- **Spec reference:** INV-ID-3 (every gateway action audited)
- **Description:** The audit record runs *after* `call_next` returns. An unhandled
  exception (mapped to 500 by Starlette's outer ServerErrorMiddleware) propagates
  through `audit_mw` before `audit.record` executes, so server-error actions —
  exactly the ones worth investigating — are never audited.
- **Evidence:** trigger any path that raises an unmapped exception (e.g. the
  git-add failure from G2-01) → 500 returned, no audit event recorded.
- **Suggested resolution:** Record in a `try/finally` (or `except` that re-raises)
  so the event is written for 5xx as well, with the resolved status/result.

## Finding G2-09: Risk/ticket inputs not range- or enum-validated
- **Severity:** Low
- **Category:** Correctness > input validation
- **Location:** `api/scree/gateway/app.py` (`assess_risk`/`create_risk` take `category: str`, `likelihood/impact: int`; `create_ticket` `origin: str`)
- **Spec reference:** risk frontmatter-schema (likelihood/impact ∈ 1..5; category/strategy enums); ticket Origin literal
- **Description:** `likelihood`/`impact` accept any int (negative, 0, 10⁶ →
  score/severity nonsense); `category`/`strategy`/`origin` accept any string
  despite being `Literal`s, so unknown enum values are persisted and silently
  never fire `fires_critical_webhook`.
- **Evidence:** `POST /risks {"likelihood":1000,"impact":1000,...}` →
  `score=1_000_000`, `severity=critical`; `category:"banana"` stored, no webhook.
- **Suggested resolution:** Validate at the boundary (Pydantic models / `conint(ge=1,le=5)`, `Literal` enums) and reject out-of-range / unknown values with 422.

## Finding G2-10: `/risks/assess` has no authentication dependency
- **Severity:** Low
- **Category:** Security > identity (consistency)
- **Location:** `api/scree/gateway/app.py:93` (`assess_risk` — no `Depends(get_principal)`)
- **Spec reference:** "single enforcement point; every action authenticated"
- **Description:** Every other endpoint requires `get_principal`; `assess_risk`
  does not, so it is callable with no identity. It is a stateless calculator (no
  data access), so impact is limited to an unauthenticated compute endpoint and an
  audit event with `principal=None`, but it breaks the "all actions authenticated"
  posture and is an unmetered compute surface.
- **Suggested resolution:** Add `Depends(get_principal)` for consistency, or
  document it as deliberately public and rate-limit it.

## Finding G2-11: Concurrent Git writes can collide on `index.lock` (no serialization)
- **Severity:** Low
- **Category:** Robustness > concurrency
- **Location:** `api/scree/knowledge/git_store.py:34-49`
- **Spec reference:** INV-ST-6 (optimistic concurrency); cross-context concurrency note
- **Description:** OCC (`base_rev`) guards lost updates at the logical level, but
  two concurrent `write`s to the same repo race on Git's `index.lock`; the loser
  gets `CalledProcessError` → 500 rather than a clean retry/conflict.
- **Evidence:** two simultaneous `POST /docs` to distinct paths in one repo can
  fail with `fatal: Unable to create '.../index.lock': File exists`.
- **Suggested resolution:** Serialize writes per repo (per-repo lock/queue) and
  surface contention as a retryable 409, not a 500.

---

## Summary

| ID | Sev | Category | Finding |
|---|---|---|---|
| G2-01 | **High** | Security/path-traversal | Arbitrary file write via doc-write `path` |
| G2-02 | **High** | Security/authz | Ticket create trusts client `requester`, ignores principal |
| G2-03 | **High** | Security/identity | Auth default-off; X-Spike-User header trusted |
| G2-04 | Medium | Security/authz | Write authority on frontmatter `space`, not `path` |
| G2-05 | Medium | Security/identity | Principal from mutable `preferred_username` not `sub` |
| G2-06 | Medium | Privacy/aggregation | community_visible views leak opaque `requester` |
| G2-07 | Medium | Robustness/DoS | YAML frontmatter unbounded (alias bomb, size) |
| G2-08 | Medium | Robustness/observability | 5xx bypasses audit middleware |
| G2-09 | Low | Correctness/input | Risk/ticket inputs not range/enum validated |
| G2-10 | Low | Security/identity | `/risks/assess` unauthenticated |
| G2-11 | Low | Robustness/concurrency | Git `index.lock` races → 500 |

**Counts:** 3 high · 5 medium · 3 low — **11 total.**

**Highest-risk area:** the doc-write path (G2-01 + G2-04) — an authenticated
writer reaches an arbitrary-location file write, and the authority decision is
decoupled from where the file actually lands.

**Recommendation / gate:** G2-01, G2-02, G2-03 are `gate:blocking` and must be
fixed before integrator phase. Per project policy all 11 are fixed before
graduation; severity sets order.

**Resolution (2026-05-28):** all 11 resolved across PRs #51 (knowledge-write
hardening: G2-01/04/07/11), #52 (gateway identity & audit: G2-02/03/05/08/10),
and #53 (validation & privacy: G2-06/09). See INDEX.md for the per-finding PR
mapping.
