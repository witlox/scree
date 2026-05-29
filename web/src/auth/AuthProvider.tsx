import { WebStorageStateStore } from "oidc-client-ts";
import type { ReactNode } from "react";
import { AuthProvider as OidcProvider } from "react-oidc-context";

import { oidcConfig } from "./config";

/** Wraps the app in the OIDC provider when configured; otherwise a passthrough so
 *  local dev (dev-header auth) needs no Keycloak. Tokens live in sessionStorage
 *  (cleared on tab close), with automatic silent renew. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const cfg = oidcConfig();
  if (!cfg) return <>{children}</>;
  return (
    <OidcProvider
      authority={cfg.authority}
      client_id={cfg.client_id}
      redirect_uri={cfg.redirect_uri}
      post_logout_redirect_uri={cfg.redirect_uri}
      scope="openid profile email"
      automaticSilentRenew
      userStore={new WebStorageStateStore({ store: window.sessionStorage })}
      onSigninCallback={() => window.history.replaceState({}, "", window.location.pathname)}
    >
      {children}
    </OidcProvider>
  );
}
