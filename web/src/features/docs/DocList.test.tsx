import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DocList } from "./DocList";

function wrap(node: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

afterEach(() => vi.restoreAllMocks());

describe("DocList", () => {
  it("renders the readable docs returned by the gateway", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(200, [
      { id: "doc-a", title: "Alpha", space: "platform/handbook" },
      { id: "doc-b", title: "Beta", space: "org/risk" },
    ])));
    wrap(<DocList onOpen={() => {}} onNew={() => {}} />);
    expect(await screen.findByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("Beta")).toBeInTheDocument();
  });

  it("shows an empty state when nothing is readable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(200, [])));
    wrap(<DocList onOpen={() => {}} onNew={() => {}} />);
    expect(await screen.findByText(/No docs you can read/i)).toBeInTheDocument();
  });

  it("shows an error state (with retry) when the request fails", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(500, { detail: "boom" })));
    wrap(<DocList onOpen={() => {}} onNew={() => {}} />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });
});
