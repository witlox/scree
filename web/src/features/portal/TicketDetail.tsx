import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "../../ui/Button";
import { TextField } from "../../ui/TextField";
import { portalApi, portalKeys } from "./api";

/** A customer's view of one ticket: status, the conversation, a reply box, and
 *  attachments (object storage). Reply + attach are participant-only server-side. */
export function TicketDetail({ ticketId, onBack }: { ticketId: string; onBack: () => void }) {
  const qc = useQueryClient();
  const ticket = useQuery({ queryKey: portalKeys.ticket(ticketId), queryFn: () => portalApi.ticket(ticketId) });
  const comments = useQuery({ queryKey: portalKeys.comments(ticketId), queryFn: () => portalApi.comments(ticketId) });
  const attachments = useQuery({ queryKey: portalKeys.attachments(ticketId), queryFn: () => portalApi.attachments(ticketId) });

  const [reply, setReply] = useState("");
  const [fileName, setFileName] = useState("");
  const [fileBody, setFileBody] = useState("");

  const sendReply = useMutation({
    mutationFn: () => portalApi.reply(ticketId, reply),
    onSuccess: () => {
      setReply("");
      void qc.invalidateQueries({ queryKey: portalKeys.comments(ticketId) });
    },
  });
  const addAttachment = useMutation({
    mutationFn: () => portalApi.attach(ticketId, fileName, fileBody),
    onSuccess: () => {
      setFileName("");
      setFileBody("");
      void qc.invalidateQueries({ queryKey: portalKeys.attachments(ticketId) });
    },
  });

  return (
    <article aria-labelledby="td-h">
      <div className="doc-toolbar">
        <Button onClick={onBack}>← My tickets</Button>
        <h2 id="td-h">{ticketId}</h2>
        {ticket.data && <span className="badge">{ticket.data.status}</span>}
      </div>

      <h3>Conversation</h3>
      {comments.isLoading && <p role="status">Loading…</p>}
      {comments.isError && <p role="alert">Couldn’t load the conversation.</p>}
      {comments.data && comments.data.length === 0 && <p>No messages yet.</p>}
      {comments.data && comments.data.length > 0 && (
        <ul className="doc-list">
          {comments.data.map((c, i) => (
            <li key={`${c.author}-${i}`}>
              <strong>{c.author}</strong>: {c.body}
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={(e) => { e.preventDefault(); sendReply.mutate(); }}>
        <TextField label="Reply" value={reply} onChange={(e) => setReply(e.target.value)} />
        <Button variant="primary" type="submit" disabled={reply.trim() === "" || sendReply.isPending}>
          {sendReply.isPending ? "Sending…" : "Send reply"}
        </Button>
        {sendReply.isError && <p role="alert" className="doc-error">Couldn’t send your reply.</p>}
      </form>

      <h3>Attachments</h3>
      {attachments.data && attachments.data.length > 0 && (
        <ul className="doc-list">
          {attachments.data.map((a) => (
            <li key={a.object_key}>{a.filename}</li>
          ))}
        </ul>
      )}
      <form onSubmit={(e) => { e.preventDefault(); addAttachment.mutate(); }}>
        <TextField label="Attachment filename" value={fileName} onChange={(e) => setFileName(e.target.value)} placeholder="screenshot.png" />
        <TextField label="Attachment content" value={fileBody} onChange={(e) => setFileBody(e.target.value)} />
        <Button type="submit" disabled={fileName.trim() === "" || addAttachment.isPending}>Attach</Button>
        {addAttachment.isError && <p role="alert" className="doc-error">Couldn’t attach (type not allowed, or too large).</p>}
      </form>
    </article>
  );
}
