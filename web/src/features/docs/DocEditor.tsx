import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { lazy, Suspense, useRef, useState } from "react";

import { Button } from "../../ui/Button";
import { TextField } from "../../ui/TextField";
import { buildDocContent, classifyWriteError, docsApi, docsKeys, type DocDetail } from "./api";
import type { TiptapApi } from "./Tiptap";

// Code-split: TipTap/ProseMirror loads only when the editor is open (a separate
// chunk), keeping it out of the initial bundle and the reader path.
const Tiptap = lazy(() => import("./Tiptap").then((m) => ({ default: m.Tiptap })));

interface Draft {
  id: string;
  path: string;
  space: string;
  title: string;
  schema_version: number;
  rev: string | null;
  body: string;
}

const FAILURE_MESSAGE: Record<string, string> = {
  governed: "This is an MR-required (governed) path — changes need a merge request, not a direct save.",
  conflict: "This doc changed since you opened it. Reload to get the latest, then re-apply your edit.",
  forbidden: "You don’t have write access to this space.",
  invalid: "The document is invalid — check the title and required fields.",
  other: "Saving failed. Please try again.",
};

/** Loader: fetch the doc to edit (or start a blank draft for a new doc), then render
 *  the form once the initial content is available so TipTap mounts with it. */
export function DocEditor({
  docId,
  isNew,
  space,
  onSaved,
  onCancel,
}: {
  docId?: string;
  isNew: boolean;
  space?: string;
  onSaved: (id: string) => void;
  onCancel: () => void;
}) {
  const detail = useQuery({
    queryKey: docsKeys.detail(docId ?? ""),
    queryFn: () => docsApi.get(docId as string),
    enabled: !isNew && !!docId,
  });

  if (isNew) {
    const blank: Draft = { id: "", path: "", space: space ?? "", title: "", schema_version: 1, rev: null, body: "" };
    return <DocEditorForm initial={blank} isNew onSaved={onSaved} onCancel={onCancel} />;
  }
  if (detail.isLoading) return <p role="status">Loading…</p>;
  if (detail.isError || !detail.data)
    return (
      <p role="alert">
        Couldn’t load the doc to edit. <button type="button" onClick={onCancel}>Cancel</button>
      </p>
    );
  return <DocEditorForm initial={fromDetail(detail.data)} isNew={false} onSaved={onSaved} onCancel={onCancel} />;
}

function fromDetail(d: DocDetail): Draft {
  return {
    id: d.id,
    path: d.path ?? "",
    space: d.space,
    title: d.title,
    schema_version: d.schema_version,
    rev: d.rev,
    body: d.body,
  };
}

function DocEditorForm({
  initial,
  isNew,
  onSaved,
  onCancel,
}: {
  initial: Draft;
  isNew: boolean;
  onSaved: (id: string) => void;
  onCancel: () => void;
}) {
  const qc = useQueryClient();
  const editorApi = useRef<TiptapApi | null>(null);
  const [title, setTitle] = useState(initial.title);
  const [id, setId] = useState(initial.id);
  const [path, setPath] = useState(initial.path);
  const [docSpace, setDocSpace] = useState(initial.space);

  const save = useMutation({
    mutationFn: () => {
      const body = editorApi.current ? editorApi.current.getMarkdown() : initial.body;
      const content = buildDocContent({ id, schema_version: initial.schema_version, title, space: docSpace, body });
      return docsApi.write({ path, content, base_rev: isNew ? null : initial.rev });
    },
    onSuccess: (res) => {
      void qc.invalidateQueries({ queryKey: docsKeys.list });
      void qc.invalidateQueries({ queryKey: docsKeys.detail(res.id) });
      void qc.invalidateQueries({ queryKey: docsKeys.versions(res.id) });
      onSaved(res.id);
    },
  });

  const failure = save.isError ? classifyWriteError(save.error) : null;
  const canSave = title.trim() !== "" && path.trim() !== "" && id.trim() !== "" && docSpace.trim() !== "";

  return (
    <form
      className="doc-editor"
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate();
      }}
    >
      <div className="doc-toolbar">
        <Button onClick={onCancel}>Cancel</Button>
        <h2>{isNew ? "New doc" : `Editing ${initial.title}`}</h2>
        <Button variant="primary" type="submit" disabled={!canSave || save.isPending}>
          {save.isPending ? "Saving…" : "Save"}
        </Button>
      </div>

      <TextField label="Title" value={title} onChange={(e) => setTitle(e.target.value)} required />

      {isNew ? (
        <>
          <TextField label="Id" value={id} onChange={(e) => setId(e.target.value)} required />
          <TextField label="Space" value={docSpace} onChange={(e) => setDocSpace(e.target.value)} required />
          <TextField label="Path" value={path} onChange={(e) => setPath(e.target.value)} placeholder="docs/page.md" required />
        </>
      ) : (
        <p className="doc-meta">{docSpace} · {path}</p>
      )}

      <Suspense fallback={<p role="status">Loading editor…</p>}>
        <Tiptap markdown={initial.body} onReady={(apiHandle) => (editorApi.current = apiHandle)} />
      </Suspense>

      {failure && <p role="alert" className="doc-error">{FAILURE_MESSAGE[failure]}</p>}
    </form>
  );
}
