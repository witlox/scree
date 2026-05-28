# Scree — Cross-Context Interactions

Which subsystems talk to which, and how — plus behavior when a downstream is
unavailable, out-of-order, or duplicated. Contexts are defined in
`domain-model.md`. The Gateway is the only enforcement point (DD-006); every
arrow that crosses a trust boundary passes through it.

---

## Interaction map

```
 web / CLI / Slack bot / email svc
                │ (OIDC token; all are Gateway clients)
                ▼
         ┌──────────────┐   validate / exchange token   ┌──────────┐
         │   GATEWAY     │◀──────────────────────────────▶│ Keycloak │
         │ authz + audit │   service creds (not hot path) ┌──────────┐
         │               │◀──────────────────────────────▶│  Vault   │
         └──┬────┬────┬──┘
   resources │    │    │ aggregation/search (filtered per-item)
 (token-exch)│    │    ▼
             ▼    │  ┌──────────┐   batch walk / critical webhook   ┌────────┐
        ┌────────┐│  │  INDEX   │◀──────────────────────────────────│ GitLab │
        │ GitLab ││  └──────────┘                                   └────────┘
        │ (repos)││        ▲
        └────────┘│        │ planning view refs (epics/iterations/milestones)
                  ▼        │
           ┌──────────────┐│
           │ object store ││  (external ticket attachments)
           └──────────────┘
```

## Interactions and their contracts

| From → To | Data | Sync? | On failure / out-of-order / duplicate |
|---|---|---|---|
| Surface → Gateway | Command/query + OIDC token | sync | Token invalid/expired → 401, re-auth; no partial state |
| Gateway → Keycloak | Token validation; token exchange | sync | FM-3/FM-5: refuse; never act as Gateway identity |
| Gateway → GitLab (as user) | Resource read/write commits | sync | FM-1: reads from clone; writes refused, never queued-as-success |
| Gateway → Vault | Service creds, signing keys | sync, cached | FM-6: cached within TTL; user auth unaffected |
| Gateway → Index | Aggregation/search query | sync | Index stale/missing → serve with "last indexed" marker; **filter per-item regardless** (INV-AGG) |
| GitLab → Indexer | Change events (critical webhook) | async | FM-7: missed webhook caught by batch; **duplicate** webhook is idempotent (re-read from Git, not payload) |
| Indexer → GitLab | Batch repo walk (hourly) | async | FM-11: resumable/idempotent; partial index not authoritative |
| Indexer → Index | Upsert derived entries | async | Rebuildable from Git (INV-ST-2); sensitive categories → separate index |
| Email svc ↔ Gateway | Inbound mail → ticket; outbound notifications | sync in, async out | FM-2/FM-13: inbound fails visibly; threading conservative; outbound retried |
| Slack bot ↔ Gateway | emoji→draft ticket; slash-link→snapshot | sync | FM-8: refuse if identity unmapped; snapshot-only (DD-012) |
| Gateway → object store | Attachment put/get | sync | FM-14: ticket text still created; attachment retried; failure surfaced |
| Planning view → Index → GitLab | Epic/iteration/milestone refs | async (read) | Stale rollup shows "as of" timestamp; references only, no duplication |

## Ordering & idempotency notes

- **Webhook vs batch race:** a webhook and the next batch may both process the
  same change. Both re-read from Git and upsert by `id`, so the operation is
  idempotent; the fresher Git state always wins (never the older payload).
- **Dual write:** the Gateway commits to Git first; index update is a *derived*
  follow-on. If the index update fails, Git is still correct and the next batch
  reconciles — there is no "commit succeeded but lost" state.
- **Concurrent writes:** the Gateway performs per-resource writes as
  read-modify-write with optimistic concurrency; on a non-fast-forward it retries
  against the latest, and irreconcilable structured-field conflicts are surfaced,
  not silently merged (INV-ST-6, FM-15).
- **Identity continuity:** the human identity must survive every hop
  (surface → Gateway → token exchange → GitLab) so the GitLab audit log attributes
  the real actor (INV-ID-1).

## Degraded-mode summary

The least resilient flow is **external ticket submission** (Surface → Gateway →
GitLab + O365 all required). Internal **reads** are the most resilient (local
clone works during a GitLab outage). Aggregation **freshness** degrades
gracefully via the "last indexed" marker; aggregation **correctness/safety**
(INV-AGG) never degrades — filtering is unconditional.
