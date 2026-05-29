import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { Markdown } from "tiptap-markdown";
import { useEffect, useRef } from "react";

/**
 * Mounts a TipTap editor (ADR-0009) into a div. Markdown is the wire format both
 * ways (tiptap-markdown). `editable=false` renders a doc read-only; the editor uses
 * `editable=true`. `onReady` hands the parent the instance to read markdown on save.
 * Remount on document change by setting a `key` on this component.
 */
export function Tiptap({
  markdown,
  editable,
  onReady,
}: {
  markdown: string;
  editable: boolean;
  onReady?: (editor: Editor) => void;
}) {
  const elRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!elRef.current) return undefined;
    const editor = new Editor({
      element: elRef.current,
      extensions: [StarterKit, Markdown],
      content: markdown,
      editable,
    });
    onReady?.(editor);
    return () => editor.destroy();
    // Mount once with the initial markdown; callers remount via `key` to load a new doc.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <div ref={elRef} className="doc-prose" data-editable={editable} />;
}
