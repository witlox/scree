# Scree

**Git-native knowledge, planning, and service desk** — a thin custom layer on top
of GitLab Ultimate (self-managed) that replaces Confluence, Atlassian Service Desk,
and the portfolio/risk gap, while keeping your data as Markdown in Git that you own.

Three surfaces, one gateway:

- **Knowledge** — a friendly editor over Markdown-in-Git for non-technical staff.
- **Customer portal** — external support over web, email, and Slack, with a
  community knowledge base.
- **Portfolio & risk** — permission-filtered rollups of GitLab epics and a 5×5
  risk register.

## Find your way

| If you want to… | Go to |
|---|---|
| Understand what Scree is and why it exists | [Why Scree](why.md) |
| Use it day-to-day | [User Guide](usage/getting-started.md) |
| &nbsp;&nbsp;• submit/track support tickets (customer) | [Customer Portal](usage/customer-portal.md) |
| &nbsp;&nbsp;• read/edit knowledge pages (staff) | [Knowledge](usage/knowledge.md) |
| &nbsp;&nbsp;• plan & track risk | [Portfolio & Risk](usage/portfolio-and-risk.md) |
| &nbsp;&nbsp;• work the support queue (agent) | [Agent Console](usage/agent-console.md) |
| Deploy and run Scree | [Operator Guide](operator-guide.md) |
| Look up a term | [Glossary](glossary.md) |
| Read the design, specs, and decisions | the *Domain & Specification*, *Architecture*, and *Decisions* sections in the sidebar |

## The shape of it in one paragraph

Your content is Markdown with YAML frontmatter in GitLab repositories. Scree reads
and edits that pile through a single API gateway, which is the *only* place
permissions are enforced — your GitLab membership decides what you can see, and
aggregations never reveal an item you couldn't open directly. Identity is
Keycloak's, secrets are Vault's, and history is Git's. If Scree went away, your
knowledge base is still a folder of Markdown you can open anywhere. See
[Why Scree](why.md) for the reasoning.
