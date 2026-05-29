import DOMPurify from "dompurify";
import { marked } from "marked";
import { useMemo } from "react";

/** Lightweight read-only markdown render. Keeps the reader path off TipTap (ADR-0003:
 *  light read surfaces). Output is sanitized — a doc author must not be able to XSS a
 *  reader of the shared KB. */
export function MarkdownView({ markdown }: { markdown: string }) {
  const html = useMemo(
    () => DOMPurify.sanitize(marked.parse(markdown, { async: false }) as string),
    [markdown],
  );
  return <div className="doc-prose" dangerouslySetInnerHTML={{ __html: html }} />;
}
