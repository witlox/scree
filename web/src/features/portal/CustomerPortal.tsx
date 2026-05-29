import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { SessionControls } from "../../auth/SessionControls";
import { Button } from "../../ui/Button";
import { TextField } from "../../ui/TextField";
import { portalApi, portalKeys } from "./api";
import { TicketDetail } from "./TicketDetail";

type View = { tab: "tickets" } | { tab: "ticket"; id: string } | { tab: "help" } | { tab: "prefs" };

/** External customer portal (#102, broadest scope): view-own + submit + reply/attach,
 *  community KB search, self-service notification prefs. Customer-facing shell (not the
 *  internal IA nav). Auth is enforced by the AuthGate around the island. */
export function CustomerPortal() {
  const [view, setView] = useState<View>({ tab: "tickets" });
  const active = view.tab === "ticket" ? "tickets" : view.tab;
  return (
    <div className="app-shell">
      <header className="app-shell__bar">
        <span className="app-shell__brand">
          <img src="/logo.png" alt="" className="app-shell__logo" />
          Scree Support
        </span>
        <nav className="app-shell__nav" aria-label="Portal">
          <button type="button" aria-current={active === "tickets" ? "page" : undefined} onClick={() => setView({ tab: "tickets" })}>My tickets</button>
          <button type="button" aria-current={active === "help" ? "page" : undefined} onClick={() => setView({ tab: "help" })}>Community help</button>
          <button type="button" aria-current={active === "prefs" ? "page" : undefined} onClick={() => setView({ tab: "prefs" })}>Notifications</button>
        </nav>
        <SessionControls />
      </header>
      <main className="app-shell__main">
        {view.tab === "tickets" && <MyTickets onOpen={(id) => setView({ tab: "ticket", id })} />}
        {view.tab === "ticket" && <TicketDetail ticketId={view.id} onBack={() => setView({ tab: "tickets" })} />}
        {view.tab === "help" && <CommunityHelp onOpen={(id) => setView({ tab: "ticket", id })} />}
        {view.tab === "prefs" && <Preferences />}
      </main>
    </div>
  );
}

function MyTickets({ onOpen }: { onOpen: (id: string) => void }) {
  const qc = useQueryClient();
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: portalKeys.myTickets, queryFn: portalApi.myTickets });
  const [desc, setDesc] = useState("");
  const submit = useMutation({
    mutationFn: () => portalApi.submit(desc),
    onSuccess: (t) => {
      setDesc("");
      void qc.invalidateQueries({ queryKey: portalKeys.myTickets });
      onOpen(t.id);
    },
  });
  return (
    <section aria-labelledby="mt-h">
      <h2 id="mt-h">My tickets</h2>
      <form onSubmit={(e) => { e.preventDefault(); submit.mutate(); }}>
        <TextField label="Describe your issue" value={desc} onChange={(e) => setDesc(e.target.value)} />
        <Button variant="primary" type="submit" disabled={desc.trim() === "" || submit.isPending}>
          {submit.isPending ? "Submitting…" : "Submit ticket"}
        </Button>
      </form>
      {isLoading && <p role="status">Loading…</p>}
      {isError && (
        <p role="alert">
          Couldn’t load your tickets. <Button onClick={() => void refetch()}>Retry</Button>
        </p>
      )}
      {data && data.length === 0 && <p>You have no tickets yet.</p>}
      {data && data.length > 0 && (
        <ul className="doc-list">
          {data.map((t) => (
            <li key={t.id}>
              <button type="button" className="doc-list__item" onClick={() => onOpen(t.id)}>
                <span className="doc-list__title">{t.id}</span>
                <span className="doc-list__space">{t.status} · {t.origin}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function CommunityHelp({ onOpen }: { onOpen: (id: string) => void }) {
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState("");
  const { data, isFetching, isError } = useQuery({
    queryKey: portalKeys.search(submitted),
    queryFn: () => portalApi.search(submitted),
    enabled: submitted !== "",
  });
  return (
    <section aria-labelledby="ch-h">
      <h2 id="ch-h">Community help</h2>
      <form onSubmit={(e) => { e.preventDefault(); setSubmitted(q); }}>
        <TextField label="Search the community knowledge base" value={q} onChange={(e) => setQ(e.target.value)} />
        <Button variant="primary" type="submit" disabled={q.trim() === ""}>Search</Button>
      </form>
      {isFetching && <p role="status">Searching…</p>}
      {isError && <p role="alert">Search failed.</p>}
      {submitted !== "" && data && data.length === 0 && <p>No community answers found.</p>}
      {data && data.length > 0 && (
        <ul className="doc-list">
          {data.map((h) => (
            <li key={h.id}>
              <button type="button" className="doc-list__item" onClick={() => onOpen(h.id)}>
                <span className="doc-list__title">{h.id}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Preferences() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: portalKeys.pref, queryFn: portalApi.getPref });
  const [pref, setPref] = useState<string | null>(null);
  const value = pref ?? data?.preference ?? "";
  const save = useMutation({
    mutationFn: () => portalApi.setPref(value),
    onSuccess: () => void qc.invalidateQueries({ queryKey: portalKeys.pref }),
  });
  return (
    <section aria-labelledby="pref-h">
      <h2 id="pref-h">Notification preferences</h2>
      {isLoading && <p role="status">Loading…</p>}
      <form onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
        <TextField
          label="When should we email you?"
          value={value}
          onChange={(e) => setPref(e.target.value)}
          placeholder="on assignment and resolution"
        />
        <Button variant="primary" type="submit" disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save"}
        </Button>
        {save.isSuccess && <p role="status">Saved.</p>}
      </form>
    </section>
  );
}
