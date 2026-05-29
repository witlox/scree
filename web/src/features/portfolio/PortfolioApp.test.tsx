import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PortfolioApp } from "./PortfolioApp";

function wrap(node: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

/** Route the mocked fetch by URL so both aggregation endpoints can be stubbed. */
function routeFetch(routes: Record<string, () => Response>) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    for (const [needle, make] of Object.entries(routes)) if (url.includes(needle)) return make();
    return json(404, { detail: "NotFound" });
  });
}

afterEach(() => vi.restoreAllMocks());

const ROLLUP = {
  epics: [{ id: "EPIC-1", title: "Platform", capacity: 8 }],
  epic_count: 1,
  total_capacity: 8,
  next_cursor: null,
  as_of: "2026-05-29T00:00:00+00:00",
  never_indexed: false,
};
const RISKS = [
  { id: "risk-1", title: "Vendor lock-in", space: "org/risk", category: "strategic", score: 16, severity: "critical", fires_critical_webhook: false },
];

describe("PortfolioApp", () => {
  it("renders the rollup totals + epics and the risk register", async () => {
    vi.stubGlobal("fetch", routeFetch({ "/planning/portfolio": () => json(200, ROLLUP), "/risks": () => json(200, RISKS) }));
    wrap(<PortfolioApp />);
    expect(await screen.findByText("Platform")).toBeInTheDocument();
    expect(screen.getByText(/1 epics · 8 capacity/)).toBeInTheDocument();
    expect(await screen.findByText("Vendor lock-in")).toBeInTheDocument();
    expect(screen.getByText("critical")).toBeInTheDocument(); // severity badge
  });

  it("shows empty states when the viewer can see nothing (INV-AGG filtered server-side)", async () => {
    const empty = { ...ROLLUP, epics: [], epic_count: 0, total_capacity: 0 };
    vi.stubGlobal("fetch", routeFetch({ "/planning/portfolio": () => json(200, empty), "/risks": () => json(200, []) }));
    wrap(<PortfolioApp />);
    expect(await screen.findByText(/No epics you can see/i)).toBeInTheDocument();
    expect(await screen.findByText(/No risks you can see/i)).toBeInTheDocument();
  });

  it("shows an error state when the rollup fails", async () => {
    vi.stubGlobal("fetch", routeFetch({ "/planning/portfolio": () => json(500, {}), "/risks": () => json(200, []) }));
    wrap(<PortfolioApp />);
    expect(await screen.findByText(/Couldn’t load the rollup/i)).toBeInTheDocument();
  });
});
