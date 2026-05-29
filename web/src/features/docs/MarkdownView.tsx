import DOMPurify from "dompurify";
import { marked } from "marked";
import { useMemo } from "react";

// FE-07: harden the sanitizer beyond defaults — drop embeds/forms/styles, and make any
// target=_blank link safe. The hook is registered once at module load.
DOMPurify.addHook("afterSanitizeAttributes", (node) => {
  if (node.tagName === "A" && node.getAttribute("target")) {
    node.setAttribute("rel", "noopener noreferrer");
  }
});
const SANITIZE_OPTS = {
  FORBID_TAGS: ["style", "iframe", "object", "embed", "form", "input", "button"],
  FORBID_ATTR: ["style", "srcset", "formaction"],
};

/** Lightweight read-only markdown render. Keeps the reader path off TipTap (ADR-0003:
 *  light read surfaces). Output is sanitized — a doc author must not be able to XSS a
 *  reader of the shared KB. */
export function MarkdownView({ markdown }: { markdown: string }) {
  const html = useMemo(
    () => DOMPurify.sanitize(marked.parse(markdown, { async: false }) as string, SANITIZE_OPTS),
    [markdown],
  );
  return <div className="doc-prose" dangerouslySetInnerHTML={{ __html: html }} />;
}
