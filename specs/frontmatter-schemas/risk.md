# Frontmatter Schema — Risk

A risk Resource. `status` ∈ {`open`, `closed`}; transition into `closed` is
MR-required (INV-LC-3, DD-009). Scoring is **5×5**; strategy is **ROAM**.
`schema_version: 1`.

## Fields (core +)

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | enum `open\|closed` | yes | Close via MR-required path only. |
| `category` | enum `delivery\|security\|compliance\|operational\|strategic` | yes | **Drives the near-real-time webhook**: `security` or `compliance` ⇒ critical (INV-IX-1). |
| `likelihood` | int 1–5 | yes | 1 = rare … 5 = almost certain. |
| `impact` | int 1–5 | yes | 1 = negligible … 5 = severe. |
| `score` | int 1–25 | yes | `likelihood × impact` (validated for consistency). |
| `severity` | enum `low\|medium\|high\|critical` | yes | **Score band** for prioritization (e.g. 1–4 low, 5–9 medium, 10–15 high, 16–25 critical). Distinct from the webhook trigger — see note. |
| `strategy` | enum `resolve\|owned\|accepted\|mitigated` | yes | ROAM. |
| `review_by` | date | yes | Next review date; overdue reviews are surfaced. |
| `affects` | object `{portfolios?, teams?, projects?}` | no | Scope of impact. |
| `mitigations` | list of references | no | Links to tickets / MRs that reduce the risk. |
| `triggers` | list[string] | no | Conditions that would realize the risk. |
| `related_risks` | list[id] | no | Cross-references. |
| `escalated_to` / `escalated_from` | id | no | Org-escalation cross-reference (DD-004). |

> **Two meanings of "critical" — do not conflate.** `severity: critical` is a
> *prioritization band* derived from `score`. The *near-real-time indexing
> webhook* fires on `category ∈ {security, compliance}`, **not** on the severity
> band (INV-IX-1, OQ-A-013). A high-`score` delivery risk is `severity: critical`
> but does **not** fire the webhook; a low-`score` security risk does.

## Example

```yaml
---
id: risk-2026-001
kind: risk
schema_version: 1
title: Atlassian cloud-only forcing function creates vendor lock-in
owner: platform-team-lead
status: open
space: org/risk-portfolio
category: strategic
likelihood: 4
impact: 4
score: 16
severity: critical
strategy: mitigated
review_by: 2026-06-01
affects: {portfolios: [engineering-platform]}
mitigations:
  - {type: tracking, target_id: ticket-2026-000045}
---

Narrative description of the risk…
```
