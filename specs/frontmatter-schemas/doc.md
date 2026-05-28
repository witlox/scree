# Frontmatter Schema — Doc

A knowledge Resource. Versioned, not stateful (no `status`). Lives at a doc path
within its Space's GitLab repo. `schema_version: 1`.

## Fields (core +)

| Field | Type | Required | Notes |
|---|---|---|---|
| `template` | enum `page\|meeting-notes\|decision\|how-to\|policy` | no | Drives editor template; `policy` typically sits on an MR-required path. |
| `summary` | string | no | One-line abstract for search/listing. |
| `review_required` | bool | no | If true, the doc's path is MR-required (DD-009); enforced by CODEOWNERS + branch protection, not by this field alone. |
| `action_items` | list of `{text, owner, done}` | no | Aggregatable across docs (meeting-notes value). |

`status` is **omitted** for docs (INV-LC: docs have versions, not states).

## Example

```yaml
---
id: doc-platform-onboarding
kind: doc
schema_version: 1
title: Platform Team Onboarding
owner: platform-team
space: platform/handbook
template: how-to
summary: How a new platform engineer gets productive in week one.
tags: [onboarding, platform]
references:
  - {type: related-doc, target_id: doc-dev-environment}
---

# Platform Team Onboarding
…markdown body…
```
