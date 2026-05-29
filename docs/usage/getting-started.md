# Getting Started

Scree has different surfaces for different people. Find yourself below, then jump
to the guide for what you actually need to do.

| You are… | You use… | Start here |
|---|---|---|
| An **external customer** | the support **portal** | [Customer Portal](customer-portal.md) |
| An **internal staff member** | **knowledge** pages | [Knowledge](knowledge.md) |
| A **planner / risk owner** | **portfolio & risk** views | [Portfolio & Risk](portfolio-and-risk.md) |
| A **support agent / desk lead** | the **agent console** | [Agent Console](agent-console.md) |
| An **operator / SRE** | the deployment | [Operator Guide](../operator-guide.md) |

## Signing in

Scree never has its own password. You sign in with your organization's identity
provider (**Keycloak**) — the same login you use for GitLab. Internal staff are
usually signed in already via single sign-on; external customers create/use a
Keycloak account when they first open the portal.

Two consequences worth knowing:

- **What you can see is what you can see in GitLab.** Scree reads your group and
  project membership from GitLab on your behalf. There is no separate "Scree
  permissions" screen to chase — ask whoever administers the relevant GitLab
  project or Space.
- **Actions are attributed to you.** When Scree writes to GitLab on your behalf
  (saving a page, transitioning a ticket), it does so *as you*, so the history
  shows the human who acted.

## Where things live

- A **Space** is a GitLab project that holds knowledge pages (and the risks that
  live with that work). "Can I see this Space?" = "Can I read this GitLab
  project?"
- A **ticket** is a customer support request, regardless of how it arrived (web,
  email, or Slack). It is private to the requester and the support team unless an
  agent deliberately publishes a curated version to the community knowledge base.
- A **risk** lives in the Space of the work it threatens, and rolls up into
  cross-project views for the people allowed to see it.

## If something looks wrong

- **You can't see a page/risk you expect to** → it's a GitLab permission; ask the
  Space's maintainer to add you to the project.
- **A save was refused with "merge request required"** → that page is governed
  (e.g. a policy); see [Knowledge → Governed pages](knowledge.md#governed-pages).
- **Everything is read-only / writes fail with "GitLab unavailable"** → Scree is
  in [graceful-degradation](../operator-guide.md#graceful-degradation) mode; reads
  still work, writes resume when GitLab is back. Tell your operator.
