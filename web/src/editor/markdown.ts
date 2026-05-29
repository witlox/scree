// Markdown round-trip through the TipTap editor (DD-016 / ADR-0009).
// Validates that markdown -> editor doc -> markdown is structurally stable.
import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { Markdown } from "tiptap-markdown";

export function roundTrip(md: string): string {
  const editor = new Editor({
    extensions: [StarterKit, Markdown],
    content: md,
  });
  try {
    // tiptap-markdown augments editor.storage at runtime but ships no type for it.
    const storage = editor.storage as unknown as { markdown: { getMarkdown(): string } };
    return storage.markdown.getMarkdown();
  } finally {
    editor.destroy();
  }
}
