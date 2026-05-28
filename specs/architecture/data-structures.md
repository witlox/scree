# Scree — Data Structures

Architectural type definitions (shape only, no method bodies). These live in
`api/schemas/` as Pydantic v2 models and are the single source of truth — the
OpenAPI spec and the TS client are generated from them (ADR-0002/0003). Names
match `specs/ubiquitous-language.md`.

> Notation is illustrative (Python type hints). Fields marked *derived* are not
> author-set; *out-of-Git* fields live in the identity directory, not frontmatter.

## Core

```python
Kind = Literal["doc", "ticket", "risk"]

class ResourceCore:
    id: str                    # opaque, kind-prefixed, Gateway-allocated (INV-ST-4)
    kind: Kind
    schema_version: int
    title: str
    owner: str                 # accountable principal/group
    space: str                 # GitLab project path
    references: list[Reference]
    tags: list[str]
    created: datetime          # derived from Git
    updated: datetime          # derived from Git

class Reference:
    type: str
    target_id: str             # withheld for cross-boundary unreadable targets (INV-REF-5)
```

## Kinds

```python
class Doc(ResourceCore):       # no status (versioned, not stateful)
    template: Literal["page","meeting-notes","decision","how-to","policy"] | None
    summary: str | None
    review_required: bool = False

TicketStatus = Literal["open", "resolved", "closed"]
Origin = Literal["email", "web", "slack", "api"]

class Ticket(ResourceCore):
    status: TicketStatus
    requester: str             # OPAQUE id; identity resolved out-of-Git (INV-DP-1)
    assignee: str | None
    watchers: list[str]        # opaque ids
    community_visible: bool = False
    encrypted: bool = False    # create-time only (INV-DP-3)
    origin: Origin
    origin_ref: dict | None
    email_token: str | None    # low-trust threading candidate (INV-EMAIL-1)

RiskStatus = Literal["open", "closed"]
RiskCategory = Literal["delivery","security","compliance","operational","strategic"]
Strategy = Literal["resolve","owned","accepted","mitigated"]   # ROAM

class Risk(ResourceCore):
    status: RiskStatus
    category: RiskCategory     # security|compliance ⇒ critical webhook (INV-IX-1)
    likelihood: int            # 1..5
    impact: int                # 1..5
    score: int                 # derived = likelihood*impact (INV; F-12)
    severity: Literal["low","medium","high","critical"]   # derived band (F-13)
    strategy: Strategy
    review_by: date
    affects: dict | None
    mitigations: list[Reference]
    escalated_to: str | None
    escalated_from: str | None
```

## Access & audit (out-of-Git / runtime)

```python
PrincipalType = Literal["internal","external","agent","operator","service","slack-bot"]

class IdentityRecord:          # identity directory — ERASABLE, out of Git (INV-DP-1/2)
    requester_id: str          # the opaque id referenced by tickets
    display_name: str
    email: str
    org_tag: str | None        # metadata, NOT a permission boundary (INV-ACC-4)

class FgaTuple:                # OpenFGA relationship (tickets only, ADR-0007)
    user: str
    relation: Literal["requester","watcher","assignee","owner"]
    object: str                # ticket id

class AuditEvent:              # append-only sink (INV-ID-3)
    principal: str
    action: str
    resource_id: str | None
    result: Literal["allow","deny","error"]
    origin: Origin | None
    at: datetime
    trace_id: str
```

## Notes

- No customer name/email appears on any in-Git structure — only `requester` opaque
  ids; `IdentityRecord` is the sole PII holder and is erasable (INV-DP-1).
- `score`/`severity` are derived; validation rejects author-set mismatches.
- Encrypted `Ticket` bodies are ciphertext at rest; this shape describes the
  decrypted, in-memory/authorized view.
