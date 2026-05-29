import { useQuery } from "@tanstack/react-query";

import { docsApi, docsKeys } from "./api";

export function DocList({ onOpen, onNew }: { onOpen: (id: string) => void; onNew: () => void }) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: docsKeys.list,
    queryFn: docsApi.list,
  });

  return (
    <section aria-labelledby="doclist-h">
      <div className="doc-toolbar">
        <h2 id="doclist-h">Docs</h2>
        <button type="button" onClick={onNew}>
          New doc
        </button>
      </div>

      {isLoading && <p role="status">Loading docs…</p>}
      {isError && (
        <p role="alert">
          Couldn’t load docs. <button type="button" onClick={() => void refetch()}>Retry</button>
        </p>
      )}
      {data && data.length === 0 && <p>No docs you can read yet.</p>}
      {data && data.length > 0 && (
        <ul className="doc-list">
          {data.map((d) => (
            <li key={d.id}>
              <button type="button" className="doc-list__item" onClick={() => onOpen(d.id)}>
                <span className="doc-list__title">{d.title}</span>
                <span className="doc-list__space">{d.space}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
