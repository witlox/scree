import type { ColumnDef } from "@tanstack/react-table";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { AppShell } from "../../ui/AppShell";
import { Button } from "../../ui/Button";
import { DataTable } from "../../ui/DataTable";
import { portfolioApi, portfolioKeys, type Epic, type RiskView } from "./api";

const epicColumns: ColumnDef<Epic>[] = [
  { accessorKey: "title", header: "Epic" },
  { accessorKey: "capacity", header: "Capacity" },
];

const riskColumns: ColumnDef<RiskView>[] = [
  { accessorKey: "title", header: "Risk" },
  { accessorKey: "category", header: "Category" },
  {
    accessorKey: "severity",
    header: "Severity",
    cell: (c) => <span className={`badge badge--${c.getValue<string>()}`}>{c.getValue<string>()}</span>,
  },
  { accessorKey: "score", header: "Score" },
  { accessorKey: "fires_critical_webhook", header: "Critical webhook", cell: (c) => (c.getValue<boolean>() ? "yes" : "no") },
];

/** Portfolio & risk aggregation (#104). Both views are filtered server-side per item
 *  (INV-AGG) — the client only renders what it is given, and never decides authority. */
export function PortfolioApp() {
  return (
    <AppShell title="Portfolio & risk" current="portfolio">
      <PortfolioRollup />
      <RiskRegister />
    </AppShell>
  );
}

function PortfolioRollup() {
  const [cursor, setCursor] = useState(0);
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: portfolioKeys.rollup(cursor),
    queryFn: () => portfolioApi.rollup(cursor),
  });

  return (
    <section aria-labelledby="rollup-h">
      <h2 id="rollup-h">Portfolio rollup</h2>
      {isLoading && <p role="status">Loading rollup…</p>}
      {isError && (
        <p role="alert">
          Couldn’t load the rollup. <Button onClick={() => void refetch()}>Retry</Button>
        </p>
      )}
      {data && (
        <>
          <p className="totals">
            {data.epic_count} epics · {data.total_capacity} capacity
            <span className="doc-meta">
              {" · "}
              {data.never_indexed ? "never indexed" : data.as_of ? `as of ${new Date(data.as_of).toLocaleString()}` : "staleness unknown"}
            </span>
          </p>
          {data.epics.length === 0 ? (
            <p>No epics you can see.</p>
          ) : (
            <DataTable caption="Portfolio epics" columns={epicColumns} data={data.epics} />
          )}
          {(cursor > 0 || data.next_cursor != null) && (
            <div className="doc-toolbar">
              <Button disabled={cursor === 0} onClick={() => setCursor(0)}>First</Button>
              <Button disabled={data.next_cursor == null} onClick={() => setCursor(data.next_cursor as number)}>
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function RiskRegister() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: portfolioKeys.risks,
    queryFn: portfolioApi.risks,
  });

  return (
    <section aria-labelledby="risks-h">
      <h2 id="risks-h">Risk register</h2>
      {isLoading && <p role="status">Loading risks…</p>}
      {isError && (
        <p role="alert">
          Couldn’t load risks. <Button onClick={() => void refetch()}>Retry</Button>
        </p>
      )}
      {data && data.length === 0 && <p>No risks you can see.</p>}
      {data && data.length > 0 && <DataTable caption="Risk register" columns={riskColumns} data={data} />}
    </section>
  );
}
