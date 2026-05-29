let handler: (() => void) | null = null;

/** Bridges a 401 from the API layer to the auth layer (FE-04): the AuthGate registers
 *  a handler that re-initiates sign-in; the query cache fires it on an unauthorized
 *  response. No-op in dev (no handler registered) — the dev-header 401 just errors. */
export const unauthorized = {
  setHandler: (h: (() => void) | null): void => {
    handler = h;
  },
  fire: (): void => handler?.(),
};
