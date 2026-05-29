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

  it("returns the config (with a fixed redirect_uri) when both vars are set", () => {
    vi.stubEnv("VITE_OIDC_AUTHORITY", "https://kc/realms/scree");
    vi.stubEnv("VITE_OIDC_CLIENT_ID", "scree-web");
    const cfg = oidcConfig();
    expect(cfg).toMatchObject({ authority: "https://kc/realms/scree", client_id: "scree-web" });
    // fixed path (default "/"), origin from jsdom — never the live page pathname (FE-02)
    expect(cfg?.redirect_uri).toBe(`${window.location.origin}/`);
  });

  it("honors a configured fixed redirect path", () => {
    vi.stubEnv("VITE_OIDC_AUTHORITY", "https://kc/realms/scree");
    vi.stubEnv("VITE_OIDC_CLIENT_ID", "scree-web");
    vi.stubEnv("VITE_OIDC_REDIRECT_PATH", "/auth/callback");
    expect(oidcConfig()?.redirect_uri).toBe(`${window.location.origin}/auth/callback`);
  });
});
