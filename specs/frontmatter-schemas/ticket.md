# Frontmatter Schema — Ticket

A service-desk Resource. `status` ∈ {`open`, `resolved`, `closed`} with reopen
(INV-LC-1). Fine-grained access is ReBAC (INV-ACC-3). `schema_version: 1`.

## Fields (core +)

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | enum `open\|resolved\|closed` | yes | Transitions: open→resolved→closed, reopen→open (INV-LC-1). |
| `requester` | string | yes | Keycloak principal (internal or external). |
| `assignee` | string | no | The agent working it. |
| `watchers` | list[string] | no | Explicitly granted viewers (INV-ACC-3); requester shares by adding here. |
| `community_visible` | bool (default `false`) | yes | Orthogonal to status; promoting requires explicit agent action (INV-LC-2, DD-013). |
| `origin` | enum `email\|web\|slack\|api` | yes | How the ticket was created (multi-channel unification). |
| `origin_ref` | object | no | Origin-specific handle: email `Message-ID`, Slack `{channel, thread_ts}`, etc. |
| `email_token` | string | no | Threading fallback token, e.g. `SCREE-123`, embedded in outbound subjects (OQ-A-014). **Low-trust:** a matching token is a threading *candidate* only; appending also requires a verified-sender match (INV-EMAIL-1). |
| `sla_due` | date-time | no | Optional SLA target surfaced to the customer. |

`owner` (core) defaults to the assignee or the desk; `space` is the service-desk
project. Default visibility is requester-private even for Slack-public origins
(DD-013).

## Example

```yaml
---
id: ticket-2026-000123
kind: ticket
schema_version: 1
title: Export fails with 500 on datasets over 2GB
owner: support-desk
status: open
space: support/service-desk
requester: ext:r.okafor@uni.example.ac
assignee: agent:dani
watchers: [ext:m.lindqvist@uni.example.ac]
community_visible: false
origin: email
origin_ref: {message_id: "<CA+abc123@mail.uni.example.ac>"}
email_token: SCREE-123
references:
  - {type: kb-article, target_id: doc-export-limits}
---

Customer reports a 500 when exporting datasets larger than ~2GB…
```
