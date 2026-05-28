# Scree — Indexer Design

The indexer maintains derived, rebuildable indexes that power search and
aggregation. **Git is truth; the index is an optimization** (INV-ST-2). Nothing
the system asserts depends on index-only state.

## Triggers (DD-005)

1. **Hourly batch** — default. A k8s CronJob (not a CI job) walks accessible repos
   and upserts changed resources. Idempotent and resumable (INV-IX-2, FM-11).
2. **Manual** — authenticated, **rate-limited** `POST /reindex` for a project or
   all (INV-IX-3); removes "I just updated this, why isn't it showing" friction.
3. **Critical webhook** — GitLab webhook fires on changes to risks whose
   `category` is `security`/`compliance` (INV-IX-1). The handler **verifies the
   signature** and **re-reads from Git** (never trusts the payload, FM-17), then
   upserts that resource only.

Degradation: webhook miss → batch catches it; batch fails → manual + webhook still
work; correctness never depends on any single trigger.

## Index structure

- **Main index** — docs, risks, planning refs, ticket metadata.
- **Sensitive index** — `security`/`compliance` risk categories, stored separately
  (INV-ENC-3 / INV-IX-4) for belt-and-suspenders against a filter bug.
- **Encrypted tickets** — indexed by **metadata only** (id/status/requester-ref/
  timestamps); bodies are not full-text indexed (INV-ENC-3).
- Every entry carries `last_indexed` so views can show an `as-of` staleness marker.

Index technology is an implementation choice (GitLab Advanced Search / Elasticsearch
reuse vs a dedicated store) — deferred; the contract here is structural.

## Aggregation query path (enforces INV-AGG)

```
request → Gateway (authn) → indexing.query
  1. query the (broad) index for candidate items
  2. filter EVERY candidate by the requester's authority:
       - tickets:   OpenFGA ListObjects(user, "read", ticket)
       - repo items: GitLab authority over the item's Space
  3. drop unauthorized items entirely (no title/count/metadata leak)
  4. return results + as-of marker
```

The filter runs per request, every request — never "filter once at view load,"
never trust the index to be pre-partitioned (DD-008).

## Rebuild & recovery

Full rebuild = drop index, re-walk all repos from Git. Recovery time is an
OQ-X-008 (DR) concern; the guarantee here is that a rebuild reproduces identical
answers (INV-ST-2).
