# Knowledge (for internal staff)

Knowledge pages are Markdown documents living in GitLab projects (Spaces). The
knowledge UI lets you browse, read, and edit them without touching Git directly.

## Browse and read

The docs list shows every page in the Spaces you can read — and **only** those.
If a colleague mentions a page you can't find, it's almost certainly in a Space
you're not a member of; ask that project's maintainer for access in GitLab.

Open a page to read it. Internal links resolve to other pages; a link to
something you can't read shows as unavailable rather than leaking its existence.

## Edit a page

Open a page and edit it in the **WYSIWYG editor**. You work in a rich view —
headings, tables, code blocks — and Scree saves clean Markdown underneath. A
no-op edit round-trips byte-for-byte, so you won't see spurious diffs.

When you save:

- A **new Git commit** records your change, attributed to you, with a timestamp.
  Pages are *versioned, not stateful* — there is no "draft/published" flag; the
  history *is* the record. Use **version history** to see or compare past edits.
- If someone edited the page since you opened it, your save is refused as a
  **conflict** rather than silently overwriting them — reload and re-apply.

## Governed pages

Some paths (typically policies, HR, compliance content) are **MR-required**.
Saving one directly is refused with *"merge request required"*. That's intentional:
governed content changes through a GitLab merge request so the right people review
it (branch protection + CODEOWNERS on the underlying repo). Make your change as an
MR in GitLab; it appears in Scree once merged.

## Tips

- **Can't see a Space** → GitLab project membership; ask its maintainer.
- **"Merge request required"** → governed path; route the change through an MR.
- **"Conflict" on save** → someone edited it first; reload and reapply.
- **Reads work but saves fail with "GitLab unavailable"** → Scree is degraded;
  your reads come from a local clone, writes resume when GitLab returns.
