import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AdminApp } from "./AdminApp";

function wrap(node: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}
function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
/** Mock fetch routed by method+URL so each admin endpoint can be stubbed. */
function routeFetch(routes: Array<{ match: (url: string, method: string) => boolean; make: () => Response }>) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    for (const r of routes) if (r.match(url, method)) return r.make();
    return json(404, { detail: "NotFound" });
  });
}

afterEach(() => vi.restoreAllMocks());

const TICKETS = [
  { id: "ticket-1", requester: "cust-okafor", status: "open", assignee: null, origin: "web", created_at: null, community_visible: false },
];

function baseRoutes(overrides: Partial<Record<string, () => Response>> = {}) {
  return [
    { match: (u: string, m: string) => u.endsWith("/tickets") && m === "GET", make: overrides.tickets ?? (() => json(200, TICKETS)) },
    { match: (u: string) => u.includes("/tickets/quarantine"), make: overrides.quarantine ?? (() => json(200, [])) },
    { match: (u: string) => u.includes("/orphans"), make: overrides.orphans ?? (() => json(200, { resources: {}, tickets: {}, as_of: null, computed: false })) },
    { match: (u: string) => u.includes("/identities/erasures"), make: overrides.erasures ?? (() => json(200, [])) },
    { match: (u: string, m: string) => /\/tickets\/ticket-1$/.test(u) && m === "PATCH", make: overrides.transition ?? (() => json(200, { id: "ticket-1", status: "resolved" })) },
    { match: (u: string, m: string) => u.includes("/identities/") && m === "DELETE", make: overrides.erase ?? (() => json(200, { identity_removed: true })) },
  ];
}

describe("AdminApp", () => {
  it("shows the ticket queue and transitions a ticket", async () => {
    const fetchMock = routeFetch(baseRoutes());
    vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);
    wrap(<AdminApp />);
    expect(await screen.findByText("ticket-1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Resolve" }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/tickets/ticket-1"),
        expect.objectContaining({ method: "PATCH" }),
      ),
    );
  });

  it("shows a role notice when quarantine review is forbidden", async () => {
    vi.stubGlobal("fetch", routeFetch(baseRoutes({ quarantine: () => json(403, { detail: "agent only" }) })) as unknown as typeof fetch);
    wrap(<AdminApp />);
    expect(await screen.findByText(/Agent access required/i)).toBeInTheDocument();
  });

  it("confirms before erasing an identity (Radix dialog)", async () => {
    const fetchMock = routeFetch(baseRoutes({ erasures: () => json(200, []) }));
    vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);
    wrap(<AdminApp />);
    const idField = await screen.findByLabelText(/Erase opaque requester id/i);
    fireEvent.change(idField, { target: { value: "ext-abc" } });
    fireEvent.click(screen.getByRole("button", { name: "Erase…" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: /Confirm erase/i }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/identities/ext-abc"),
        expect.objectContaining({ method: "DELETE" }),
      ),
    );
  });
});
