import { useQuery } from "@tanstack/react-query";

import { docsApi, docsKeys } from "./api";

export function VersionHistory({ docId }: { docId: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: docsKeys.versions(docId),
    queryFn: () => docsApi.versions(docId),
  });

  if (isLoading) return <p role="status">Loading history…</p>;
  if (isError) return <p role="alert">Couldn’t load version history.</p>;
  if (!data || data.length === 0) return <p>No version history.</p>;

  return (
    <ol className="doc-versions">
      {data.map((v) => (
        <li key={v.rev}>
          <code className="doc-versions__rev">{v.rev.slice(0, 8)}</code>{" "}
          <span>{v.message}</span>{" "}
          <span className="doc-versions__meta">
            {v.author} · {new Date(v.date).toLocaleString()}
          </span>
        </li>
      ))}
    </ol>
  );
}
