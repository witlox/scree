import type { ComponentType } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { mountIslands } from "./mountIslands";

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("mountIslands", () => {
  it("mounts a registered island into its data-island node with props", async () => {
    document.body.innerHTML = `<div data-island="demo" data-props='{"label":"Hi"}'></div>`;
    const Demo: ComponentType<Record<string, unknown>> = (props) => (
      <span>island:{String(props.label ?? "")}</span>
    );

    const count = mountIslands({ demo: Demo });

    expect(count).toBe(1);
    await vi.waitFor(() => expect(document.body.textContent).toContain("island:Hi"));
  });

  it("skips an unregistered island name and warns", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    document.body.innerHTML = `<div data-island="missing"></div>`;
    expect(mountIslands({})).toBe(0);
    expect(warn).toHaveBeenCalledOnce();
  });

  it("ignores empty placeholder nodes", () => {
    document.body.innerHTML = `<div data-island=""></div>`;
    expect(mountIslands({})).toBe(0);
  });
});
