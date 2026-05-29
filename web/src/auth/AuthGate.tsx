import { type ReactNode, useEffect } from "react";
import { useAuth } from "react-oidc-context";

import { oidcConfig } from "./config";
import { tokenStore } from "./tokenStore";

/** Gates a surface behind a real session when OIDC is configured. Unconfigured (dev)
 *  → passthrough (dev-header auth). Configured → loading/error/redirect-to-IdP until
 *  authenticated, and keeps ApiClient's bearer in sync via the token store. */
export function AuthGate({ children }: { children: ReactNode }) {
  if (!oidcConfig()) return <>{children}</>;
  return <Gate>{children}</Gate>;
}

function Gate({ children }: { children: ReactNode }) {
  const auth = useAuth();

  useEffect(() => {
    tokenStore.set(auth.isAuthenticated && auth.user ? auth.user.access_token : null);
  }, [auth.isAuthenticated, auth.user]);

  useEffect(() => {
    if (!auth.isLoading && !auth.isAuthenticated && !auth.error && !auth.activeNavigator) {
      void auth.signinRedirect();
    }
  }, [auth.isLoading, auth.isAuthenticated, auth.error, auth.activeNavigator, auth.signinRedirect]);

  if (auth.error)
    return (
      <p role="alert">
        Sign-in failed: {auth.error.message}{" "}
        <button type="button" onClick={() => void auth.signinRedirect()}>
          Try again
        </button>
      </p>
    );
  if (!auth.isAuthenticated) return <p role="status">Signing in…</p>;
  return <>{children}</>;
}
