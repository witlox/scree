import { QueryCache, QueryClient } from "@tanstack/react-query";

import { ApiError } from "../../api";
import { unauthorized } from "../../auth/session";

/** Server state lives in the query cache (not a global store). Conservative defaults:
 *  short stale window, one retry, no refetch-on-focus (avoids surprising re-auths).
 *  A 401 on any query re-initiates sign-in via the auth bridge (FE-04). */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: (error) => {
        if (error instanceof ApiError && error.status === 401) unauthorized.fire();
      },
    }),
    defaultOptions: {
      queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
    },
  });
}
