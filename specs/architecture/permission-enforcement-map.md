# Scree — Invariant → Enforcement Map

Every invariant from `specs/invariants.md` mapped to the architectural point that
enforces it and the mechanism. The architect consistency check is: **no invariant
without an enforcement point.** Security-critical rows (INV-AGG, INV-ACC, INV-ID,
INV-ENC, INV-DP) are called out for the auditor.

## Storage & references

| Invariant | Enforcement point | Mechanism |
|---|---|---|
| INV-ST-1 (Git is truth) | `gateway` write path | every mutation is a Git commit via `integration/gitlab`; no state lives only in cache/index |
| INV-ST-2 (index rebuildable) | `indexing` | index is derived; full rebuild job from Git |
| INV-ST-3 (schema_version) | `schemas` validation at write + CI | reject resources lacking `schema_version` |
| INV-ST-4 (id allocation) | `gateway` | per-kind sequence allocator; ids minted server-side |
| INV-ST-5 (created/updated derived) | `integration/gitlab` | values read from commit history, never authored |
| INV-ST-6 (optimistic concurrency) | `gateway` write path | read-modify-write; retry on non-fast-forward; conflicting structured fields surfaced |
| INV-REF-1..4 (references) | `gateway` render + `schemas` | references by id; tombstone; unreadable target → "unavailable" |
| INV-REF-5 (id opacity) | `gateway` render layer | withhold `target_id` of cross-boundary unreadable referents |

## Access & permissions (SECURITY-CRITICAL)

| Invariant | Enforcement point | Mechanism |
|---|---|---|
| **INV-AGG** (no aggregation leak) | `indexing` aggregation queries, behind `gateway` | ticket authority = **OpenFGA `ListObjects` ∪ GitLab desk-repo membership** (agents see all via repo, AR-04); repo items via the requester's resolved readable-Spaces set (resolved once, AR-08); filter every item per-request; sensitive risk categories in a separate index |
| INV-ACC-1 (single enforcement point) | `gateway` | all clients hit the Gateway; adapters hold no backend access; exception: authorized offline reads of client-key content |
| INV-ACC-2 (RBAC ∪ ReBAC) | `access` authority composition | GitLab repo/group authority OR OpenFGA relation grants |
| INV-ACC-3 (ticket visibility) | `access` + OpenFGA | requester/watcher/assignee/agent relations; `community_visible` snapshot |
| INV-ACC-4 (org tag ≠ access) | `access` | org tag is metadata; never consulted for authorization |
| INV-ACC-5 (cache fails closed) | `access` permission cache | short TTL; omit on uncertainty |

## Identity & audit (SECURITY-CRITICAL)

| Invariant | Enforcement point | Mechanism |
|---|---|---|
| INV-ID-1 (human in GitLab audit) | `access` token exchange | RFC 8693; GitLab-user principals only |
| INV-ID-2 (Slack unmapped → refuse) | `integration/slack` + `access` | resolve Slack→Keycloak; refuse if unmapped |
| INV-ID-3 (audit everything) | `access` audit sink | append-only, integrity-protected sink for all Gateway actions incl. reads/queries |
| INV-ID-4 (external write attribution) | `gateway` + `integration/gitlab` | desk service-account commit; external id in trailer + app audit |
| INV-EMAIL-1 (verified inbound) | `integration/o365` | DKIM/DMARC; token = candidate; sender-match-or-quarantine |
| INV-SLACK-1 (capture rules) | `integration/slack` | author=requester; capturer recorded; rate-limited |

## Encryption & data protection (SECURITY-CRITICAL)

| Invariant | Enforcement point | Mechanism |
|---|---|---|
| INV-ENC-1 (selective encryption) | `crypto` + write path | SOPS+age (sensitive spaces) / Vault Transit (tagged/born-encrypted tickets) |
| INV-ENC-2 (key model) | `crypto` | age recipient keys (client) / per-requester Transit key (gateway) |
| INV-ENC-3 (index protection) | `indexing` | encrypted tickets metadata-only; index access-controlled |
| INV-ENC-4 (rotation-based revocation) | ops | re-encrypt to new recipient set |
| INV-DP-1 (PII out of Git) | `access` identity directory | erasable store; Git holds opaque requester id |
| INV-DP-2 (erasure = anonymize) | `access` | delete identity record (+ delete Transit key to crypto-shred) |
| INV-DP-3 (born-encrypted, create-time) | `gateway` + `servicedesk` | `encrypted` set at create; not retroactive |
| INV-DP-4 (bounded by GitLab) | architecture-wide | documented posture; no stronger-than-substrate promise |

## Lifecycle, governance, indexing, orphans, degradation, migration

| Invariant | Enforcement point | Mechanism |
|---|---|---|
| INV-LC-1/3 (ticket/risk states) | `servicedesk`/`risk` state machine | reject illegal transitions; close-risk on MR path |
| INV-LC-2 (community_visible) | `servicedesk` | resolved-only, confirmed, curated snapshot, reopen re-gates |
| INV-LC-4 (risk escalation) | `risk` | duplicate into org Space + cross-ref |
| INV-GOV-1 (MR-required paths) | **GitLab** branch protection + CODEOWNERS | enforced at the substrate, not the app |
| INV-IX-1 (critical webhook) | `indexing` + GitLab webhook | fires on category security/compliance |
| INV-IX-2/3/4 (batch/manual/separate index) | `indexing` | hourly batch (k8s CronJob); rate-limited manual; sensitive split index |
| INV-ORPH-1/2 (orphans) | `indexing` batch | flag owner-lost-access actives + unassigned/departed-assignee tickets |
| INV-DEG-1/2 (degradation) | `gateway` + clients | clone reads; writes refused, never queued-as-success |
| INV-MIG-1/2/3 (migration) | `migration` | ID-mapping table; idempotent; non-curated → archive |

## Gaps / escalations

None blocking. Items deferred to other owners: cache implementation detail
(OQ-A-011, architect impl), HA specifics for Gateway/OpenFGA (ADR-0010 follow-up),
DR/residency of the identity directory + index (OQ-X-008, OQ-HE-005).
