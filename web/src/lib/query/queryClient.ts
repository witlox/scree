import { QueryClient } from "@tanstack/react-query";

/** Server state lives in the query cache (not a global store). Conservative defaults:
 *  short stale window, one retry, no refetch-on-focus (avoids surprising re-auths). */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
    },
  });
}
