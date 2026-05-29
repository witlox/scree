import { oidcConfig } from "../auth/config";
import { tokenStore } from "../auth/tokenStore";
import { ApiClient } from "./client";

export { ApiClient, ApiError } from "./client";
export type { ApiPaths } from "./client";

/**
 * The shared API client. `getToken` reads the live OIDC access token (set by the
 * AuthGate); when OIDC is NOT configured (local dev / the demo image) it falls back
 * to the gateway's dev-header path (`?as=<user>` or VITE_DEV_USER). Gating on
 * `oidcConfig()` (not `import.meta.env.DEV`) lets the built demo image use the dev
 * header too. This is safe: the gateway only honors the header when started with
 * `allow_insecure_header_auth` (dev) — a real deployment runs OIDC + ignores it.
 */
function devUser(): string | undefined {
  if (oidcConfig()) return undefined; // real auth configured → no dev header
  const fromQuery = new URLSearchParams(window.location.search).get("as");
  return fromQuery ?? (import.meta.env.VITE_DEV_USER as string | undefined) ?? "rivera";
}

export const api = new ApiClient({ baseUrl: "/api", getToken: () => tokenStore.get(), devUser: devUser() });
