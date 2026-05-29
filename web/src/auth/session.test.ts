import { describe, expect, it, vi } from "vitest";

import { unauthorized } from "./session";

describe("unauthorized bridge (FE-04)", () => {
  it("fires the registered handler, and no-ops once cleared", () => {
    const handler = vi.fn();
    unauthorized.setHandler(handler);
    unauthorized.fire();
    expect(handler).toHaveBeenCalledOnce();

    unauthorized.setHandler(null);
    unauthorized.fire(); // no handler → no-op, no throw
    expect(handler).toHaveBeenCalledOnce();
  });
});
