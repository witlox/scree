import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MarkdownView } from "./MarkdownView";

describe("MarkdownView", () => {
  it("renders markdown as formatted HTML", () => {
    const { container } = render(<MarkdownView markdown={"# Title\n\nsome **bold** text"} />);
    expect(container.querySelector("h1")?.textContent).toBe("Title");
    expect(container.querySelector("strong")?.textContent).toBe("bold");
  });

  it("strips script, iframe, and event handlers (FE-07: no author XSS)", () => {
    const malicious = [
      "<script>window.__pwned = 1</script>",
      '<img src=x onerror="window.__pwned=1">',
      '<iframe src="https://evil.example"></iframe>',
      "[ok](javascript:alert(1))",
    ].join("\n\n");
    const { container } = render(<MarkdownView markdown={malicious} />);
    const html = container.innerHTML;
    expect(html).not.toContain("<script");
    expect(html).not.toContain("<iframe");
    expect(html.toLowerCase()).not.toContain("onerror");
    expect(html.toLowerCase()).not.toContain("javascript:");
  });
});
