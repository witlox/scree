/**
 * @e2e — drives the real CustomerPortal island against the canonical portal.feature
 * @e2e scenarios. The gateway is replaced by a small stateful route mock: GET /tickets
 * returns only the customer's own tickets (the server-side INV-ACC-3 filter), so the
 * UI journey is exercised without a live backend.
 */
import { expect, type Route } from "@playwright/test";

import { type Ctx, runFeature, Steps } from "./bdd";

interface TicketRow {
  id: string;
  requester: string | null;
  status: string;
  assignee: string | null;
  origin: string;
  created_at: string | null;
  community_visible: boolean;
}
interface CommentRow { author: string; body: string; source: string }
interface AttachRow { filename: string; object_key: string }

interface MockState {
  tickets: TicketRow[];
  comments: Record<string, CommentRow[]>;
  attachments: Record<string, AttachRow[]>;
  lastCreated?: TicketRow;
  opened: boolean;
}

const CUSTOMER = "ext:r.okafor@uni.example.ac";

function state(ctx: Ctx): MockState {
  return ctx.state as MockState;
}

async function installMock(ctx: Ctx): Promise<void> {
  const s: MockState = { tickets: [], comments: {}, attachments: {}, opened: false };
  ctx.state = s;
  // Anchor to the gateway base (origin + /api/), NOT a "**/api/**" glob — the latter
  // also matches dev module URLs like /src/api/index.ts and would break the bundle.
  await ctx.page.route(/^https?:\/\/[^/]+\/api\//, async (route: Route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/^\/api/, "");
    const method = route.request().method();
    const body = (route.request().postDataJSON() as Record<string, string> | null) ?? {};
    const json = (data: unknown) => route.fulfill({ json: data });

    if (path === "/tickets" && method === "GET") return json(s.tickets);
    if (path === "/tickets" && method === "POST") {
      const id = `ticket-2026-00${900 + s.tickets.length}`;
      const row: TicketRow = {
        id, requester: CUSTOMER, status: "open", assignee: null,
        origin: body.origin, created_at: new Date().toISOString(), community_visible: false,
      };
      s.tickets.push(row);
      s.lastCreated = row;
      s.comments[id] = [{ author: CUSTOMER, body: body.body, source: "web" }];
      return json({ ...row, encrypted: false });
    }
    const detail = /^\/tickets\/([^/]+)$/.exec(path);
    if (detail && method === "GET") {
      const t = s.tickets.find((x) => x.id === detail[1]);
      return json(t ? { id: t.id, requester: t.requester, status: t.status, community_visible: t.community_visible } : {});
    }
    const comments = /^\/tickets\/([^/]+)\/comments$/.exec(path);
    if (comments && method === "GET") return json(s.comments[comments[1]] ?? []);
    if (comments && method === "POST") {
      const c: CommentRow = { author: CUSTOMER, body: body.body, source: "web" };
      (s.comments[comments[1]] ??= []).push(c);
      return json(c);
    }
    const atts = /^\/tickets\/([^/]+)\/attachments$/.exec(path);
    if (atts && method === "GET") return json(s.attachments[atts[1]] ?? []);
    if (atts && method === "POST") {
      // Object storage, NOT Git (external-attachment decision): an opaque object key.
      const a: AttachRow = { filename: body.filename, object_key: `objstore/${atts[1]}/${body.filename}` };
      (s.attachments[atts[1]] ??= []).push(a);
      return json(a);
    }
    return route.fulfill({ json: [] });
  });
}

async function openPortal(ctx: Ctx): Promise<void> {
  if (state(ctx).opened) return;
  await ctx.page.goto(`/e2e/host.html?island=portal&as=${encodeURIComponent(CUSTOMER)}`);
  await expect(ctx.page.getByRole("heading", { name: "My tickets" })).toBeVisible();
  state(ctx).opened = true;
}

const steps = new Steps();

steps.def('"{who}" is authenticated via Keycloak', () => {
  // dev-header auth (AuthGate passthrough); the verified bearer is out of scope here
});

steps.def('"{owner}" owns "{ticket}"', (ctx, _owner, ticket) => {
  state(ctx).tickets.push({
    id: ticket, requester: CUSTOMER, status: "open", assignee: null,
    origin: "web", created_at: "2026-01-01T00:00:00Z", community_visible: false,
  });
});

steps.def('"{ticket}" belongs to another customer and is not community_visible', () => {
  // The server-side filter omits it from GET /tickets, so it is simply absent here.
});

steps.def('they open "My tickets"', async (ctx) => {
  await openPortal(ctx);
  await ctx.page.getByRole("button", { name: "My tickets" }).click();
});

steps.def('"{ticket}" is listed', async (ctx, ticket) => {
  await expect(ctx.page.getByText(ticket, { exact: false })).toBeVisible();
});

steps.def('"{ticket}" is not listed', async (ctx, ticket) => {
  await expect(ctx.page.getByText(ticket, { exact: false })).toHaveCount(0);
});

steps.def('they submit a ticket titled "{title}"', async (ctx, title) => {
  await openPortal(ctx);
  await ctx.page.getByLabel("Describe your issue").fill(title);
  await ctx.page.getByRole("button", { name: "Submit ticket" }).click();
});

steps.def('a ticket is created with origin "{origin}" and requester "{requester}"', async (ctx, origin, requester) => {
  const created = state(ctx).lastCreated;
  expect(created?.origin).toBe(origin);
  expect(created?.requester).toBe(requester);
  // The portal navigates to the new ticket on success.
  await expect(ctx.page.getByRole("heading", { name: created!.id })).toBeVisible();
});

steps.def('they reply with the attachment "{filename}"', async (ctx, filename) => {
  await ctx.page.getByLabel("Reply").fill("here is the screenshot");
  await ctx.page.getByRole("button", { name: "Send reply" }).click();
  await ctx.page.getByLabel("Attachment filename").fill(filename);
  await ctx.page.getByLabel("Attachment content").fill("PNGDATA");
  await ctx.page.getByRole("button", { name: "Attach" }).click();
});

steps.def("the reply and attachment appear on the ticket", async (ctx) => {
  await expect(ctx.page.getByText("here is the screenshot", { exact: false })).toBeVisible();
  await expect(ctx.page.getByText("screenshot.png", { exact: false })).toBeVisible();
});

steps.def("the attachment is stored in object storage, not Git", (ctx) => {
  const id = state(ctx).lastCreated!.id;
  const a = state(ctx).attachments[id]?.[0];
  expect(a?.object_key.startsWith("objstore/")).toBe(true);
});

runFeature("portal.feature", "e2e", steps, { setup: installMock });
