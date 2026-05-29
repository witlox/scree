import { type ReactNode, useEffect } from "react";
import { useAuth } from "react-oidc-context";

import { oidcConfig } from "./config";
import { unauthorized } from "./session";
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

  // FE-01: sync the bearer DURING render. The parent renders before its children, so
  // the children's first query effects fire with the token already in the store — not
  // after a useEffect that would run too late and emit an unauthenticated 401.
  tokenStore.set(auth.isAuthenticated && auth.user ? auth.user.access_token : null);

  // FE-04: a 401 from any request (session expired/revoked) re-initiates sign-in
  // instead of surfacing a dead-end error.
  useEffect(() => {
    unauthorized.setHandler(() => void auth.signinRedirect());
    return () => unauthorized.setHandler(null);
  }, [auth.signinRedirect]);

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
