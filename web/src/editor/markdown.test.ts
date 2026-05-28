import { describe, expect, it } from "vitest";

import { roundTrip } from "./markdown";

const SAMPLE = `# Onboarding

Some **bold** text, then a list:

- first
- second

\`\`\`python
print("hi")
\`\`\`
`;

describe("TipTap markdown round-trip (DD-016)", () => {
  it("preserves core structures", () => {
    const out = roundTrip(SAMPLE);
    expect(out).toContain("Onboarding");
    expect(out).toContain("bold");
    expect(out).toContain("first");
    expect(out).toContain("second");
    expect(out).toContain('print("hi")');
    expect(out).toContain("```");
  });

  it("is idempotent (stable round-trip)", () => {
    const once = roundTrip(SAMPLE);
    expect(roundTrip(once)).toBe(once);
  });
});
