import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { docsApi, docsKeys } from "./api";
import { MarkdownView } from "./MarkdownView";
import { VersionHistory } from "./VersionHistory";

export function DocView({
  docId,
  onEdit,
  onBack,
}: {
  docId: string;
  onEdit: (id: string) => void;
  onBack: () => void;
}) {
  const [showHistory, setShowHistory] = useState(false);
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: docsKeys.detail(docId),
    queryFn: () => docsApi.get(docId),
  });

  if (isLoading) return <p role="status">Loading…</p>;
  if (isError || !data)
    return (
      <p role="alert">
        Couldn’t load this doc. <button type="button" onClick={() => void refetch()}>Retry</button>{" "}
        <button type="button" onClick={onBack}>Back</button>
      </p>
    );

  return (
    <article aria-labelledby="docview-h">
      <div className="doc-toolbar">
        <button type="button" onClick={onBack}>← Docs</button>
        <h2 id="docview-h">{data.title}</h2>
        <button type="button" onClick={() => onEdit(docId)}>Edit</button>
        <button type="button" aria-pressed={showHistory} onClick={() => setShowHistory((v) => !v)}>
          History
        </button>
      </div>
      <p className="doc-meta">{data.space}{data.updated ? ` · updated ${new Date(data.updated).toLocaleString()}` : ""}</p>
      {/* lightweight read render (no TipTap on the read path) */}
      <MarkdownView markdown={data.body} />
      {showHistory && <VersionHistory docId={docId} />}
    </article>
  );
}
