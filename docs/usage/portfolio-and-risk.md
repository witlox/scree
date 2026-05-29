# Portfolio & Risk (for planners and risk owners)

These views aggregate work and risk *across* GitLab projects, while showing each
viewer only what they're allowed to see.

## Portfolio rollup

The portfolio view rolls up GitLab epics/iterations into a cross-project picture.
It is **permission-filtered per request**: an epic in a group you can't read does
not contribute to the rollup, and its existence is not revealed — not its title,
not the count, not its capacity. The totals you see are computed from visible
items only.

Because the rollup is built from an index that refreshes periodically, the view
shows an **"as of" timestamp** so you can tell how fresh it is. A stale rollup is
labelled, never presented as live.

## Risk register

Risks are scored on a **5×5** matrix (likelihood × impact) with a derived severity
band, and carry a **ROAM** strategy (Resolve / Owned / Accepted / Mitigated). A
risk lives in the Space of the work it threatens.

To work with risks:

- **Create a risk** with a likelihood (1–5) and impact (1–5); Scree computes the
  score and severity band for you. You can only create risks in a Space you can
  write to.
- **Assess** a likelihood/impact/category combination to preview its score,
  severity, and whether it would trigger near-real-time indexing — without saving.
- **Cross-project register** shows risks from every Space you can read, and
  excludes the rest. As with the portfolio, **no count, score, title, or excerpt**
  of a risk you can't read is ever exposed.

### How urgent risks get noticed faster

A **security** or **compliance** risk fires a near-real-time indexing webhook, so
it surfaces in search almost immediately. Other categories (e.g. delivery) ride
the regular hourly batch. Either way the risk is indexed — the category only
changes *how fast*.

### Closing and escalating

- **Escalating** a project risk creates an org-level duplicate that cross-
  references the original (which stays put), so portfolio owners can track it
  without losing the project context.
- **Closing** a risk on a governed path goes through a merge request, like any
  governed change — the close is reviewed, not a silent edit.

> Note: escalation and close-via-MR are modeled in the domain today but not yet
> exposed as portal actions — your operator/CLI performs them. See the roadmap.
