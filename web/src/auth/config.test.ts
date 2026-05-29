import { afterEach, describe, expect, it, vi } from "vitest";

import { oidcConfig } from "./config";

afterEach(() => vi.unstubAllEnvs());

describe("oidcConfig", () => {
  it("is null when the OIDC env is unset (dev-header path stays active)", () => {
    expect(oidcConfig()).toBeNull();
  });

  it("is null if only one of the two vars is set", () => {
    vi.stubEnv("VITE_OIDC_AUTHORITY", "https://kc/realms/scree");
    expect(oidcConfig()).toBeNull();
  });

  it("returns the config when both vars are set", () => {
    vi.stubEnv("VITE_OIDC_AUTHORITY", "https://kc/realms/scree");
    vi.stubEnv("VITE_OIDC_CLIENT_ID", "scree-web");
    expect(oidcConfig()).toEqual({ authority: "https://kc/realms/scree", client_id: "scree-web" });
  });
});
