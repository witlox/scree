let current: string | null = null;

/** Bridges the React auth session to the module-singleton ApiClient: the AuthGate
 *  writes the current access token here, and ApiClient.getToken reads it per request.
 *  Keeps the client decoupled from React without scattering tokens through components. */
export const tokenStore = {
  get: (): string | null => current,
  set: (token: string | null): void => {
    current = token;
  },
};
