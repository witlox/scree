import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CustomerPortal } from "./CustomerPortal";

function wrap(node: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}
function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
function routeFetch(routes: Array<{ match: (u: string, m: string) => boolean; make: () => Response }>) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    for (const r of routes) if (r.match(url, method)) return r.make();
    return json(404, { detail: "NotFound" });
  });
}
afterEach(() => vi.restoreAllMocks());

const ONE_TICKET = [{ id: "ticket-7", requester: "cust-okafor", status: "open", assignee: null, origin: "web", created_at: null, community_visible: false }];

describe("CustomerPortal", () => {
  it("lists the customer's own tickets and opens one", async () => {
    vi.stubGlobal("fetch", routeFetch([
      { match: (u, m) => u.endsWith("/tickets") && m === "GET", make: () => json(200, ONE_TICKET) },
      { match: (u) => /\/tickets\/ticket-7$/.test(u), make: () => json(200, { id: "ticket-7", requester: "cust-okafor", status: "open", community_visible: false }) },
      { match: (u) => u.includes("/comments"), make: () => json(200, [{ author: "cust-okafor", body: "it broke", source: "api" }]) },
      { match: (u) => u.includes("/attachments"), make: () => json(200, []) },
    ]) as unknown as typeof fetch);
    wrap(<CustomerPortal />);
    fireEvent.click(await screen.findByRole("button", { name: /ticket-7/ }));
    expect(await screen.findByText(/it broke/)).toBeInTheDocument();
  });

  it("sends a reply on a ticket", async () => {
    const fetchMock = routeFetch([
      { match: (u, m) => u.endsWith("/tickets") && m === "GET", make: () => json(200, ONE_TICKET) },
      { match: (u) => /\/tickets\/ticket-7$/.test(u), make: () => json(200, { id: "ticket-7", requester: "cust-okafor", status: "open", community_visible: false }) },
      { match: (u, m) => u.includes("/comments") && m === "GET", make: () => json(200, []) },
      { match: (u, m) => u.includes("/comments") && m === "POST", make: () => json(200, { author: "cust-okafor", body: "any update?", source: "web" }) },
      { match: (u) => u.includes("/attachments"), make: () => json(200, []) },
    ]);
    vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);
    wrap(<CustomerPortal />);
    fireEvent.click(await screen.findByRole("button", { name: /ticket-7/ }));
    fireEvent.change(await screen.findByLabelText("Reply"), { target: { value: "any update?" } });
    fireEvent.click(screen.getByRole("button", { name: /Send reply/i }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/tickets/ticket-7/comments"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });

  it("searches the community KB", async () => {
    vi.stubGlobal("fetch", routeFetch([
      { match: (u, m) => u.endsWith("/tickets") && m === "GET", make: () => json(200, []) },
      { match: (u) => u.includes("/community/search"), make: () => json(200, [{ id: "ticket-pub" }]) },
    ]) as unknown as typeof fetch);
    wrap(<CustomerPortal />);
    fireEvent.click(screen.getByRole("button", { name: "Community help" }));
    const region = screen.getByRole("region", { name: /Community help/i });
    fireEvent.change(within(region).getByLabelText(/Search the community/i), { target: { value: "reset" } });
    fireEvent.click(within(region).getByRole("button", { name: "Search" }));
    expect(await screen.findByText("ticket-pub")).toBeInTheDocument();
  });
});
