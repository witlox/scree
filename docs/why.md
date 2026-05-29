# Why Scree

Scree exists because an organization decided to leave Atlassian's cloud, and
discovered that "leaving" is really three problems wearing one coat:

1. **Knowledge** lived in Confluence.
2. **External support** lived in Atlassian Service Desk.
3. **Portfolio and risk** lived in a patchwork of Jira plugins and spreadsheets.

GitLab Ultimate (self-managed) already covers code, issues, epics, iterations,
and CI. Scree is the thin layer on top that covers the three things GitLab does
*not* — without standing up another cloud vendor to be locked into next.

## The one idea

**Your content is Markdown with YAML frontmatter, in Git.** A knowledge page, a
risk, a migrated Confluence article — they are files in a GitLab repository, with
real history, real diffs, and real access control. Scree is a *reader and editor*
over that pile, not a database that happens to export to Markdown.

That choice is the reason for almost everything else:

- **You own your data.** If Scree disappeared tomorrow, your knowledge base is
  still a folder of Markdown you can open in any editor. There is no proprietary
  store to escape from. (This is the whole point — it is the lock-in we left.)
- **History is the audit trail.** "Who changed this and when" is a `git log`, not
  a feature we had to build and you have to trust.
- **Permissions come from GitLab.** If you can read a project in GitLab, you can
  read its Space in Scree. We do not maintain a second copy of "who can see what"
  for knowledge — there is one source of truth.

## What Scree is

Three surfaces, one gateway:

- **Knowledge** — a friendly UI over Markdown-in-Git for *non-technical* people.
  Browse, search, and edit with a WYSIWYG editor that round-trips clean Markdown.
  Designated pages (policies, HR) require a merge request instead of a direct save.
- **Customer portal** — external customers submit and track support tickets over
  the web, by email, or from a public Slack channel; search a community knowledge
  base of resolved answers; and manage their own notification preferences.
- **Portfolio & risk** — cross-project rollups of GitLab epics/iterations and a
  5×5 risk register with ROAM strategies, aggregated across projects — showing you
  only the items you are actually allowed to see.

## What Scree is *not*

- **Not a replacement for GitLab.** Issues, epics, code, CI, and repo permissions
  stay in GitLab. Scree reuses them.
- **Not a second identity store.** Keycloak is the source of identity; Scree never
  invents its own accounts.
- **Not a second secrets store.** Vault holds service credentials.
- **Not an offline system.** If GitLab is unreachable, Scree degrades gracefully —
  you can still *read* from a local clone, and writes are refused *clearly* rather
  than silently dropped — but full disconnected operation is out of scope.

## The invariant worth knowing as a user

**An aggregation never shows you something you couldn't open directly.** A
portfolio rollup, a cross-project risk view, a community search — each filters
every item against your GitLab/ticket permissions, per request. You will never see
the *title, count, or score* of a risk in a project you can't read. If that
guarantee ever appears to break, it is a bug, not a feature — report it.

For where to go next, see the [User Guide](usage/getting-started.md) (for everyday
use) or the [Operator Guide](operator-guide.md) (to deploy and run Scree).
