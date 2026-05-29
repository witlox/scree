# Customer Portal (for external customers)

The portal is where customers raise and follow support requests. You reach it in a
browser, sign in with your Keycloak account, and land on **My tickets**.

## Submit a ticket

There are three ways to open a ticket — they all become the same kind of record:

- **Web** — on *My tickets*, describe your issue in the box and choose **Submit
  ticket**. You're taken straight to the new ticket.
- **Email** — send a message to the support address. A verified email becomes a
  ticket automatically; replies thread onto it (by email headers, or by the
  `[SCREE-NNN]` token in the subject if your client strips headers). An email that
  can't be verified is held for an agent to review rather than silently attributed.
- **Slack** — in the public community channel, react to a message with `:ticket:`.
  The thread is captured as a snapshot and a private ticket is created for you.

Every ticket starts **private** to you and the support team — even one captured
from a public Slack thread. Nothing you submit is public unless an agent later
publishes a curated answer to the community knowledge base.

## Track and reply

Open a ticket from **My tickets** to see its status and conversation. You can:

- **Reply** — add a message; the agent sees it on their side.
- **Attach a file** — e.g. `screenshot.png`. Attachments are stored in object
  storage (not in Git), and a few executable file types are rejected for safety.

You only ever see **your own** tickets. Another customer's ticket never appears in
your list, even if you both contacted the same team.

## Search the community knowledge base

**Community help** searches resolved tickets that an agent has chosen to publish.
Results are curated snapshots — never live private threads — so a follow-up reply
on a published ticket never leaks into search. If your question matches one, you
may get your answer without opening a ticket at all.

## Notification preferences

Under **Notifications**, set when Scree emails you (for example, *"on assignment
and resolution"*). The preference is saved to your account and applies to future
notifications.

## What stays private

- Your email address and name are **never** written into Git. Scree stores an
  opaque id on the ticket and keeps the mapping to your real contact details
  separately. Agents can see who you are; the public knowledge base cannot.
- If you ask to be erased (GDPR), your identity record is deleted, your tickets'
  requester id becomes unresolvable, and any encrypted content is crypto-shredded.
  See your support team or DPO to request this.
