import { tokenStore } from "../auth/tokenStore";
import { ApiClient } from "./client";

export { ApiClient, ApiError } from "./client";
export type { ApiPaths } from "./client";

/**
 * The shared API client. `getToken` reads the live OIDC access token (set by the
 * AuthGate); when there is none (local dev without Keycloak) it falls back to the
 * gateway's dev-header path. Dev user comes from `?as=<user>` or VITE_DEV_USER.
 */
function devUser(): string | undefined {
  if (!import.meta.env.DEV) return undefined;
  const fromQuery = new URLSearchParams(window.location.search).get("as");
  return fromQuery ?? (import.meta.env.VITE_DEV_USER as string | undefined) ?? "rivera";
}

export const api = new ApiClient({ baseUrl: "/api", getToken: () => tokenStore.get(), devUser: devUser() });
