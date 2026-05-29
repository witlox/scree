export interface OidcConfig {
  authority: string; // Keycloak realm issuer, e.g. https://keycloak.example/realms/scree
  client_id: string; // the public SPA client (auth-code + PKCE)
}

/**
 * OIDC config from the build env, or null when unset. Null = the dev-header path
 * (X-Spike-User) stays active for local dev without a Keycloak. Production sets both
 * vars, which switches the app to the real auth-code + PKCE login (INV-ID-1). The
 * realm/client/audience config (the SPA token's `aud` must satisfy the gateway's
 * OidcAuthenticator) is a deploy concern — see .env.example.
 */
export function oidcConfig(): OidcConfig | null {
  const authority = import.meta.env.VITE_OIDC_AUTHORITY as string | undefined;
  const clientId = import.meta.env.VITE_OIDC_CLIENT_ID as string | undefined;
  if (!authority || !clientId) return null;
  return { authority, client_id: clientId };
}
