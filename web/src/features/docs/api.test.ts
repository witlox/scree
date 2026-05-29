import { describe, expect, it } from "vitest";

import { ApiError } from "../../api";
import { buildDocContent, classifyWriteError } from "./api";

describe("buildDocContent", () => {
  it("emits valid frontmatter with the doc identity and body", () => {
    const out = buildDocContent({
      id: "doc-a",
      schema_version: 1,
      title: "Onboarding",
      space: "platform/handbook",
      body: "# Hello\n\nbody",
    });
    expect(out).toBe(
      [
        "---",
        "id: doc-a",
        "kind: doc",
        "schema_version: 1",
        'title: "Onboarding"',
        'space: "platform/handbook"',
        "---",
        "# Hello",
        "",
        "body",
        "",
      ].join("\n"),
    );
  });

  it("quotes titles with punctuation so the frontmatter can't break", () => {
    const out = buildDocContent({ id: "d", schema_version: 1, title: 'A: "tricky"', space: "s", body: "x" });
    expect(out).toContain('title: "A: \\"tricky\\""');
  });
});

describe("classifyWriteError", () => {
  const err = (status: number, detail: string) => new ApiError(status, "x", { detail });
  it("maps governed, conflict, forbidden, invalid", () => {
    expect(classifyWriteError(err(409, "MRRequired"))).toBe("governed");
    expect(classifyWriteError(err(409, "Conflict"))).toBe("conflict");
    expect(classifyWriteError(err(409, "GitWriteError"))).toBe("conflict");
    expect(classifyWriteError(err(403, "Forbidden"))).toBe("forbidden");
    expect(classifyWriteError(err(422, "InvalidFrontmatter"))).toBe("invalid");
  });
  it("falls back to 'other' for non-ApiError", () => {
    expect(classifyWriteError(new Error("boom"))).toBe("other");
  });
});
