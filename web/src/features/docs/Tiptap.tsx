import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { Markdown } from "tiptap-markdown";
import { useEffect, useRef } from "react";

/** Imperative handle the editor hands to its parent, so the parent can read markdown
 *  on save WITHOUT statically importing TipTap (keeps this whole module code-split). */
export interface TiptapApi {
  getMarkdown: () => string;
}

/**
 * Editable TipTap surface (ADR-0009). Markdown is the wire format (tiptap-markdown).
 * This module is loaded lazily by the editor only, so TipTap/ProseMirror stay out of
 * the reader and initial bundle (the reader renders markdown via MarkdownView).
 */
export function Tiptap({
  markdown,
  onReady,
}: {
  markdown: string;
  onReady?: (api: TiptapApi) => void;
}) {
  const elRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!elRef.current) return undefined;
    const editor = new Editor({
      element: elRef.current,
      extensions: [StarterKit, Markdown],
      content: markdown,
      editable: true,
    });
    // tiptap-markdown augments editor.storage at runtime but ships no type for it.
    const storage = editor.storage as unknown as { markdown: { getMarkdown(): string } };
    onReady?.({ getMarkdown: () => storage.markdown.getMarkdown() });
    return () => editor.destroy();
    // Mount once with the initial markdown.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <div ref={elRef} className="doc-prose doc-prose--editable" data-editable="true" />;
}
