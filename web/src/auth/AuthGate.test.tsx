import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { tokenStore } from "./tokenStore";

interface MockAuth {
  isAuthenticated: boolean;
  isLoading: boolean;
  error?: Error;
  activeNavigator?: string;
  user: { access_token: string } | null;
  signinRedirect: () => void;
}

// Hoisted so the vi.mock factory can safely reference them.
const h = vi.hoisted(() => ({
  auth: { current: null as MockAuth | null },
  configured: { current: true },
  signinRedirect: vi.fn(),
}));

vi.mock("react-oidc-context", () => ({ useAuth: () => h.auth.current }));
vi.mock("./config", () => ({ oidcConfig: () => (h.configured.current ? { authority: "a", client_id: "c" } : null) }));

import { AuthGate } from "./AuthGate";

beforeEach(() => {
  h.signinRedirect.mockClear();
  h.configured.current = true;
  tokenStore.set(null);
});
afterEach(() => {
  document.body.innerHTML = "";
});

describe("AuthGate", () => {
  it("renders children and syncs the token when authenticated", () => {
    h.auth.current = {
      isAuthenticated: true,
      isLoading: false,
      user: { access_token: "tok-1" },
      signinRedirect: h.signinRedirect,
    };
    render(
      <AuthGate>
        <p>secret</p>
      </AuthGate>,
    );
    expect(screen.getByText("secret")).toBeInTheDocument();
    expect(tokenStore.get()).toBe("tok-1");
  });

  it("redirects to the IdP and hides children when not authenticated", async () => {
    h.auth.current = { isAuthenticated: false, isLoading: false, user: null, signinRedirect: h.signinRedirect };
    render(
      <AuthGate>
        <p>secret</p>
      </AuthGate>,
    );
    expect(screen.getByRole("status")).toHaveTextContent(/Signing in/i);
    expect(screen.queryByText("secret")).toBeNull();
    await waitFor(() => expect(h.signinRedirect).toHaveBeenCalled());
  });

  it("surfaces a sign-in error with a retry", () => {
    h.auth.current = { isAuthenticated: false, isLoading: false, error: new Error("boom"), user: null, signinRedirect: h.signinRedirect };
    render(
      <AuthGate>
        <p>secret</p>
      </AuthGate>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/boom/);
  });

  it("passes through (no gate) when OIDC is unconfigured (dev)", () => {
    h.configured.current = false;
    render(
      <AuthGate>
        <p>secret</p>
      </AuthGate>,
    );
    expect(screen.getByText("secret")).toBeInTheDocument();
  });
});
