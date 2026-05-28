# Adversary — Implementation Gate 1 Findings

Adversarial pass over the merged implementation (`api/`), after the spike + first
implementer slices (PRs #33–#44). Distinguishes **real bugs/inconsistencies in
shipped code** from **scope gaps** (specced, not yet built). Same policy: all
fixed before this phase graduates; severity sets order.

---

## Real bugs / inconsistencies in shipped code

### I-01 — A customer cannot read the ticket they just created
- **Severity:** High
- **Where:** `servicedesk/service.py::create`, `access/ticket_authority.py`
- **Description:** `create` stores the ticket but writes **no OpenFGA `requester`
  relation**. So `can_read`/`readable_tickets` deny the requester their own
  ticket — create and read are inconsistent. (Flagged as a scope cut, but it makes
  the create→read flow broken end-to-end.)
- **Fix:** on create, grant the requester the `requester` relation (write the tuple
  via the authority/relations).

### I-02 — `community_visible` grants no read access
- **Severity:** High
- **Where:** `access/ticket_authority.py::can_read` / `readable_tickets`
- **Description:** Authority is `agents ∪ relations` only — it never consults
  `community_visible`. Promoting a ticket (INV-LC-2) therefore does **nothing** for
  other authenticated principals; INV-ACC-3 ("readable by any authenticated
  principal when community_visible") is unenforced.
- **Fix:** `can_read` returns true when the ticket is `community_visible`; the
  authority needs the ticket (not just its id) to check the flag.

### I-04 — Re-writing identical doc content crashes (500)
- **Severity:** Medium
- **Where:** `knowledge/git_store.py::write`
- **Description:** `git commit` with `check=True` fails ("nothing to commit") when
  content is unchanged, raising `CalledProcessError` → 500. A no-op save crashes.
- **Fix:** detect "no changes" and return cleanly (or `--allow-empty`-free skip).

### I-05 — Malformed frontmatter (missing closing `---`) → 500
- **Severity:** Medium
- **Where:** `knowledge/frontmatter.py::parse`
- **Description:** `text.split("---", 2)` then unpacking three values raises
  `ValueError` (not `InvalidFrontmatter`) when there is no closing `---` → 500
  instead of a clean 422.
- **Fix:** validate there are 3 parts; raise `InvalidFrontmatter` otherwise.

### I-09 — Risk register is hollow (predicate not wired; no persistence)
- **Severity:** Medium
- **Where:** `risk/*`, gateway
- **Description:** `fires_critical_webhook` is a correct but **dead** predicate —
  no indexer/webhook calls it; risks aren't persisted, listed, or aggregated. The
  "register" can't actually register anything. INV-IX-1 is validated as a function,
  not enforced in a flow.
- **Fix (later round):** risk persistence via the doc-write (Git) path + wire the
  trigger into the indexer.

---

## Security model not yet enforced (known spike stubs — must not ship as-is)

### I-03 — Identity is an untrusted header; real authz not wired into the Gateway
- **Severity:** High (for production; accepted for the spike)
- **Where:** `gateway/app.py` (X-Spike-User), default `create_app` wiring
- **Description:** The request path trusts `X-Spike-User` outright — anyone can
  claim any principal. `RealOpenFga`/`GitLabAuthority` exist but are wired only in
  `@contract` tests, not in `create_app`. So INV-ACC-1 (single enforcement point),
  INV-ID-1/2 (OIDC, token exchange, attribution) are **not enforced** in shipped
  code, and the Git commit author (#I-08 below) is spoofable.
- **Fix (later round):** OIDC auth dependency + token exchange; wire RealOpenFga +
  GitLabAuthority into `create_app`. Tracked: OQ-A-016, ADR-0007/0018.

### I-08 — No audit anywhere (INV-ID-3)
- **Severity:** Medium
- **Description:** Not a single Gateway action is recorded. The append-only audit
  sink (INV-ID-3, AR-10) is unimplemented.
- **Fix (later round):** audit middleware writing to the append-only sink.

---

## Spec-vs-code gaps (specced, deferred)

### I-06 — Doc write: no id allocation / uniqueness / kind check (INV-ST-4)
- **Severity:** Medium
- **Description:** `id` is taken from author-supplied frontmatter; no Gateway
  allocation, no global-uniqueness enforcement, no check that `kind == "doc"`. Two
  docs can collide ids; a doc endpoint accepts a `kind: ticket` body; path reuse can
  overwrite a different doc.

### I-07 — Doc write: no optimistic concurrency (INV-ST-6)
- **Severity:** Medium
- **Description:** Concurrent writes to the same path are last-writer-wins; no
  base-revision check. INV-ST-6 unenforced.

### I-10 — Error handling is per-endpoint, not the central handler
- **Severity:** Low
- **Description:** `error-taxonomy.md` specifies one central exception handler;
  the code raises `HTTPException` ad hoc per endpoint. Works, but drifts.

---

## Summary

**Fix now (this round):** I-01, I-02 (High correctness), I-04, I-05 (Medium
robustness) — they make shipped features partly broken.
**Next rounds:** I-03 (real auth — the big one before any real use), I-08 (audit),
I-06/I-07 (write integrity), I-09 (risk persistence), I-10 (central errors).
