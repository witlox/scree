export interface OidcConfig {
  authority: string; // Keycloak realm issuer, e.g. https://keycloak.example/realms/scree
  client_id: string; // the public SPA client (auth-code + PKCE)
  redirect_uri: string; // FE-02: a FIXED registered callback, not the live pathname
}

/**
 * OIDC config from the build env, or null when unset. Null = the dev-header path
 * (X-Spike-User) stays active for local dev without a Keycloak. Production sets the
 * vars, which switches the app to the real auth-code + PKCE login (INV-ID-1).
 *
 * `redirect_uri` is a FIXED path (VITE_OIDC_REDIRECT_PATH, default "/") so it can be
 * registered once with Keycloak — never the live `window.location.pathname`, which
 * would vary per surface and (with a wildcard client) be an open-redirect vector
 * (FE-02). The realm/client/audience config is a deploy concern — see .env.example.
 */
export function oidcConfig(): OidcConfig | null {
  const authority = import.meta.env.VITE_OIDC_AUTHORITY as string | undefined;
  const clientId = import.meta.env.VITE_OIDC_CLIENT_ID as string | undefined;
  if (!authority || !clientId) return null;
  const redirectPath = (import.meta.env.VITE_OIDC_REDIRECT_PATH as string | undefined) ?? "/";
  return { authority, client_id: clientId, redirect_uri: window.location.origin + redirectPath };
}
