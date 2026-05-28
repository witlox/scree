# Adversary — Architecture Gate 2 Findings

Spec-level adversarial pass over `specs/architecture/`, gating architect→
implementer. Same policy: **every finding is fixed before graduation**; severity
sets order.

---

## AR-01 — Client-key encrypted docs can't be server-rendered by the web UI
- **Severity:** High
- **Category:** Correctness > contradiction
- **Location:** ADR-0008; `module-graph.md` (`web/knowledge` htmx/SSR); `context-graph.md`
- **Spec ref:** ADR-0005/0008 (client-side age keys), ADR-0003 (htmx SSR)
- **Description:** ADR-0008 puts internal sensitive-space content under **client-side** age keys — the **server never holds the key**. But the knowledge web surface renders docs **server-side** (htmx/SSR). The Gateway therefore cannot decrypt a sensitive-space doc to render it. Client-side keys and server-side rendering are mutually exclusive for that content.
- **Evidence:** A user opens a doc in a `security` doc-space via the web UI → Gateway fetches ciphertext → has no age key → cannot render.
- **Suggested resolution (needs a decision):** Either (a) sensitive-space docs are **clone/CLI-only** (not shown in the web UI) — honest with the client-key model; or (b) provide **in-browser client-side decryption** (the user's key in the browser, never the server) for those spaces; or (c) use **Gateway-mediated keys** for sensitive *docs* too (like tickets), losing offline-read for them. Pick one explicitly.

## AR-02 — Non-Git stores lack DR commensurate with criticality (Transit-key loss = mass loss)
- **Severity:** High
- **Category:** Robustness > durability
- **Location:** `deployment-topology.md`; ADR-0006/0008
- **Description:** "Backups are clones" only covers Git. The **Vault Transit keys**, **identity directory** (sole PII copy), OpenFGA datastore, and index are out-of-Git. **Losing the Transit keys permanently destroys every encrypted ticket** (accidental org-wide crypto-shred); losing the identity directory loses all customer identities. These need backup/DR at least as robust as Git's — currently unspecified (OQ-X-008 open but this raises its severity).
- **Suggested resolution:** Specify backup/restore + residency for Transit keys (Vault DR), the identity directory, OpenFGA, and the index; treat Transit-key backup as tier-1.

## AR-03 — OpenFGA vs Git source-of-truth for ticket relations is ambiguous
- **Severity:** High
- **Category:** Correctness > dual source of truth
- **Location:** `integration-contracts/README.md` (OpenFGA), `indexer-design.md`, INV-ST-1/2
- **Description:** Ticket relations (`requester/watcher/assignee/owner`) appear both in the ticket **frontmatter (Git)** and as **OpenFGA tuples**. It's unstated which is authoritative. If OpenFGA is authoritative, it's a second source of truth not rebuildable from Git (violates INV-ST-1/2) and a dual-write hazard (Git commit succeeds, tuple write fails, or vice versa).
- **Suggested resolution:** Declare **Git frontmatter the source of truth**; OpenFGA is a **derived, rebuildable projection**. Gateway writes Git first, then upserts tuples; a reconciler rebuilds tuples from Git (mirrors INV-ST-2). Specify the dual-write failure handling.

## AR-04 — Ticket aggregation via ListObjects alone under-grants agents
- **Severity:** High
- **Category:** Correctness > permission composition
- **Location:** `indexer-design.md` (aggregation query path), `permission-enforcement-map.md` INV-AGG
- **Description:** Agents see **all** tickets via **desk-repo membership** (GitLab), not via per-ticket OpenFGA tuples. The aggregation filter says "tickets → OpenFGA `ListObjects`", which would return only tickets where the agent has an explicit relation — **omitting the agent's blanket view**. Conversely external customers get tickets via OpenFGA, not repo membership. The filter must compose **both**.
- **Suggested resolution:** Ticket authority in aggregation = OpenFGA `ListObjects` (relation grants) **∪** GitLab desk-repo membership (agent blanket read). Make the union explicit in the query path (matches INV-ACC-2).

## AR-05 — Erasure doesn't purge OpenFGA tuples for the erased requester
- **Severity:** Medium
- **Category:** Security > stale authority
- **Location:** INV-DP-2; `integration-contracts/README.md` (OpenFGA)
- **Description:** Erasure deletes the identity record + crypto-shreds the Transit key, but OpenFGA tuples referencing the requester's opaque id are not mentioned. Stale tuples = lingering (dangling) authority references.
- **Suggested resolution:** Erasure also deletes all OpenFGA tuples for the requester id; add to the erasure flow and INV-DP-2.

## AR-06 — Encrypted-ticket title/metadata is cleartext and may carry PII
- **Severity:** Medium
- **Category:** Security > privacy
- **Location:** `data-structures.md` (`ResourceCore.title`), INV-ENC-3
- **Description:** Encrypted tickets are "metadata-only" indexed, but `title` (and other core metadata) is cleartext in Git and the index. A born-encrypted ticket's title can itself contain PII ("Reset password for jane@uni.example").
- **Suggested resolution:** For encrypted tickets, encrypt or redact the title (store a neutral placeholder in cleartext); decide what cleartext metadata is permissible.

## AR-07 — Identity directory availability / degraded mode unspecified (new SPOF)
- **Severity:** Medium
- **Category:** Robustness > availability
- **Location:** `context-graph.md` (degraded-mode table omits it), `module-graph.md`
- **Description:** The identity directory (Postgres) is a new out-of-Git dependency for customer-facing flows (display, notification, DSAR). It's absent from the degraded-mode table and the "reads work during GitLab outage" story. Its outage behavior is undefined.
- **Suggested resolution:** Add the identity directory to the degraded-mode table; authz (opaque ids) should not depend on it, but resolution/notification does — define the degraded behavior.

## AR-08 — GitLab per-item authority evaluation method unspecified (perf/DoS)
- **Severity:** Medium
- **Category:** Robustness > resource exhaustion
- **Location:** `indexer-design.md` (aggregation query path)
- **Description:** "Filter every candidate by GitLab authority over its Space" implies up to N GitLab API calls per query — a latency/DoS problem on large result sets.
- **Suggested resolution:** Resolve the requester's set of readable Spaces **once** (cached, short TTL) and filter candidates locally against it; never per-item API calls.

## AR-09 — Migration must populate the identity directory + OpenFGA, not just Git
- **Severity:** Medium
- **Category:** Correctness > completeness
- **Location:** `module-graph.md` (`migration/`), `migration.feature`, INV-MIG
- **Description:** JSM tickets carry customer identities and relations. The migration writes tickets to Git but must also populate the **identity directory** (PII, erasable) and **OpenFGA tuples**, and respect the opaque-id model. Currently only the Git side is implied.
- **Suggested resolution:** Migration populates Git + identity directory + OpenFGA atomically; imported PII enters the erasable directory under the same model.

## AR-10 — Audit sink store + tamper-evidence + retention not realized
- **Severity:** Medium
- **Category:** Security > audit
- **Location:** `deployment-topology.md` (no audit store workload), INV-ID-3 (F-05)
- **Description:** F-05 was resolved at the invariant level ("append-only, integrity-protected sink"), but the architecture doesn't realize it: no audit store in the topology, no tamper-evidence mechanism, no retention.
- **Suggested resolution:** Add the audit store to the topology; specify append-only + integrity (hash chain or WORM) + retention (ties to OQ-HE-005).

## AR-11 — INV-AGG depends on OpenFGA ListObjects performance at scale (unvalidated)
- **Severity:** Medium
- **Category:** Robustness > performance dependency
- **Location:** `indexer-design.md`, `permission-enforcement-map.md`, assumption A-5
- **Description:** The load-bearing aggregation filter leans on `ListObjects`, which can be expensive on large object sets. This rests on unvalidated ★A-5.
- **Suggested resolution:** Add an OQ-X-006 perf target for `ListObjects`; validate in the spike; define a fallback (e.g., bounded result + pagination) if it doesn't meet target.

## AR-12 — 404-collapse may confuse users who previously had access
- **Severity:** Low
- **Category:** Correctness > UX (not security)
- **Location:** `error-taxonomy.md` (`NotFoundOrUnauthorized`)
- **Description:** Collapsing missing/forbidden to 404 is correct for existence-leak prevention but can confuse a user who legitimately lost access to something they saw before.
- **Suggested resolution:** Accept for cross-boundary cases; optionally give a softer message for same-Space ownership changes where no existence leak is possible.

---

## Cross-cutting note

AR-01/02/03 are the structural ones to settle before implementation: the
**client-key-vs-web-rendering** contradiction (AR-01), **DR for the non-Git
crown jewels** (AR-02, esp. Transit keys), and **Git-as-truth for relations**
(AR-03). AR-04 is a correctness bug in the headline INV-AGG path. The rest are
tighten-and-specify.
