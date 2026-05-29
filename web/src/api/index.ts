import { ApiClient } from "./client";

export { ApiClient, ApiError } from "./client";
export type { ApiPaths } from "./client";

/**
 * The shared API client. In dev it uses the gateway's header auth (X-Spike-User);
 * the real OIDC bearer flow replaces `devUser` with `getToken` once login lands.
 * Dev user comes from `?as=<user>` or VITE_DEV_USER, defaulting to a sample.
 */
function devUser(): string | undefined {
  if (!import.meta.env.DEV) return undefined;
  const fromQuery = new URLSearchParams(window.location.search).get("as");
  return fromQuery ?? (import.meta.env.VITE_DEV_USER as string | undefined) ?? "rivera";
}

export const api = new ApiClient({ baseUrl: "/api", devUser: devUser() });
