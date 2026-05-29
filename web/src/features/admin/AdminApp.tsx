import type { ColumnDef } from "@tanstack/react-table";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { AppShell } from "../../ui/AppShell";
import { Button } from "../../ui/Button";
import { DataTable } from "../../ui/DataTable";
import { Dialog } from "../../ui/Dialog";
import { TextField } from "../../ui/TextField";
import {
  adminApi,
  adminKeys,
  isForbidden,
  nextTransitions,
  type ErasureReceipt,
  type QuarantineItem,
  type TicketSummary,
} from "./api";

/** Internal admin/agent console (#103): ticket queue + transitions, quarantine review,
 *  orphan report, and the DPO erasure console. Role checks are server-side; the UI shows
 *  a clear notice on 403 and never relies on hiding for security. */
export function AdminApp() {
  return (
    <AppShell title="Admin" current="admin">
      <TicketQueue />
      <QuarantineReview />
      <OrphanReport />
      <ErasureConsole />
    </AppShell>
  );
}

function TicketQueue() {
  const qc = useQueryClient();
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: adminKeys.tickets, queryFn: adminApi.tickets });
  const transition = useMutation({
    mutationFn: (v: { id: string; status: string }) => adminApi.transition(v.id, v.status),
    onSuccess: () => void qc.invalidateQueries({ queryKey: adminKeys.tickets }),
  });

  const columns: ColumnDef<TicketSummary>[] = [
    { accessorKey: "id", header: "Ticket" },
    { accessorKey: "status", header: "Status" },
    { accessorKey: "origin", header: "Origin" },
    { accessorKey: "requester", header: "Requester", cell: (c) => c.getValue<string | null>() ?? "—" },
    {
      id: "actions",
      header: "Actions",
      enableSorting: false,
      cell: ({ row }) => (
        <span className="doc-toolbar">
          {nextTransitions(row.original.status).map((a) => (
            <Button key={a.status} disabled={transition.isPending} onClick={() => transition.mutate({ id: row.original.id, status: a.status })}>
              {a.label}
            </Button>
          ))}
        </span>
      ),
    },
  ];

  return (
    <section aria-labelledby="queue-h">
      <h2 id="queue-h">Ticket queue</h2>
      {isLoading && <p role="status">Loading tickets…</p>}
      {isError && (
        <p role="alert">
          Couldn’t load tickets. <Button onClick={() => void refetch()}>Retry</Button>
        </p>
      )}
      {data && data.length === 0 && <p>No tickets in your queue.</p>}
      {data && data.length > 0 && <DataTable caption="Ticket queue" columns={columns} data={data} />}
      {transition.isError && <p role="alert" className="doc-error">That transition isn’t allowed.</p>}
    </section>
  );
}

function QuarantineReview() {
  const { data, isLoading, error, isError } = useQuery({ queryKey: adminKeys.quarantine, queryFn: adminApi.quarantine });
  const columns: ColumnDef<QuarantineItem>[] = [
    { accessorKey: "claimed_from", header: "Claimed from" },
    { accessorKey: "subject", header: "Subject" },
    { accessorKey: "reason", header: "Reason", cell: (c) => c.getValue<string | null>() ?? "—" },
    { accessorKey: "candidate_ticket", header: "Candidate", cell: (c) => c.getValue<string | null>() ?? "—" },
  ];
  return (
    <section aria-labelledby="quar-h">
      <h2 id="quar-h">Quarantine review</h2>
      {isLoading && <p role="status">Loading…</p>}
      {isError && isForbidden(error) && <p role="alert">Agent access required.</p>}
      {isError && !isForbidden(error) && <p role="alert">Couldn’t load the quarantine queue.</p>}
      {data && data.length === 0 && <p>Quarantine is empty.</p>}
      {data && data.length > 0 && <DataTable caption="Quarantined mail" columns={columns} data={data} />}
    </section>
  );
}

function OrphanReport() {
  const { data, isLoading, isError } = useQuery({ queryKey: adminKeys.orphans, queryFn: adminApi.orphans });
  const entries = (group: Record<string, string[]>) => Object.entries(group);
  return (
    <section aria-labelledby="orph-h">
      <h2 id="orph-h">Orphaned actives</h2>
      {isLoading && <p role="status">Loading…</p>}
      {isError && <p role="alert">Couldn’t load the orphan report.</p>}
      {data && !data.computed && <p>Not computed yet (awaiting the batch refresh).</p>}
      {data && data.computed && entries(data.resources).length === 0 && entries(data.tickets).length === 0 && (
        <p>No orphaned actives in your scope.</p>
      )}
      {data && data.computed && (
        <ul className="doc-list">
          {entries(data.resources).map(([space, ids]) => (
            <li key={`r-${space}`}>
              <strong>{space}</strong> — risks: {ids.join(", ")}
            </li>
          ))}
          {entries(data.tickets).map(([desk, ids]) => (
            <li key={`t-${desk}`}>
              <strong>{desk}</strong> — tickets: {ids.join(", ")}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ErasureConsole() {
  const qc = useQueryClient();
  const { data, isLoading, error, isError } = useQuery({ queryKey: adminKeys.erasures, queryFn: adminApi.erasures });
  const [target, setTarget] = useState("");
  const [confirming, setConfirming] = useState(false);
  const erase = useMutation({
    mutationFn: (opaqueId: string) => adminApi.erase(opaqueId),
    onSuccess: () => {
      setConfirming(false);
      setTarget("");
      void qc.invalidateQueries({ queryKey: adminKeys.erasures });
    },
  });

  const columns: ColumnDef<ErasureReceipt>[] = [
    { accessorKey: "subject", header: "Subject" },
    { accessorKey: "actor", header: "Actor" },
    { accessorKey: "at", header: "At" },
    { accessorKey: "relations_purged", header: "Relations purged" },
  ];

  return (
    <section aria-labelledby="dpo-h">
      <h2 id="dpo-h">Erasure (DPO)</h2>
      {isLoading && <p role="status">Loading…</p>}
      {isError && isForbidden(error) && <p role="alert">Compliance / DPO access required.</p>}
      {isError && !isForbidden(error) && <p role="alert">Couldn’t load the erasure log.</p>}
      {data && (
        <>
          <div className="doc-toolbar">
            <TextField label="Erase opaque requester id" value={target} onChange={(e) => setTarget(e.target.value)} />
            <Button variant="primary" disabled={target.trim() === ""} onClick={() => setConfirming(true)}>
              Erase…
            </Button>
          </div>
          <Dialog open={confirming} onOpenChange={setConfirming} title={`Erase ${target}?`}>
            <p>
              This anonymizes the customer record and purges their relations and quarantine — it cannot be undone.
              Git history is retained (residual disclosed in the receipt).
            </p>
            <div className="doc-toolbar">
              <Button onClick={() => setConfirming(false)}>Cancel</Button>
              <Button variant="primary" disabled={erase.isPending} onClick={() => erase.mutate(target)}>
                {erase.isPending ? "Erasing…" : "Confirm erase"}
              </Button>
            </div>
            {erase.isError && <p role="alert" className="doc-error">Erase failed.</p>}
          </Dialog>
          {data.length === 0 ? (
            <p>No erasures recorded.</p>
          ) : (
            <DataTable caption="Erasure receipts" columns={columns} data={data} />
          )}
        </>
      )}
    </section>
  );
}
