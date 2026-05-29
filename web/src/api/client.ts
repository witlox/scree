import type { paths } from "./schema";

/** The generated OpenAPI paths — the single source of truth for request/response
 *  shapes. Feature code derives types from this; never hand-write them. */
export type ApiPaths = paths;

/** Supplies the current OIDC bearer (or null when unauthenticated). */
export type TokenProvider = () => string | null | Promise<string | null>;

export interface ApiClientOptions {
  baseUrl?: string;
  getToken?: TokenProvider;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * The ONLY path to the backend (see .claude/coding/typescript.md). It attaches the
 * OIDC bearer so GitLab's audit shows the human (INV-ID-1); authorization is the
 * gateway's job, never the client's. No ad-hoc `fetch` elsewhere.
 */
export class ApiClient {
  private readonly baseUrl: string;
  private readonly getToken: TokenProvider;

  constructor(opts: ApiClientOptions = {}) {
    this.baseUrl = (opts.baseUrl ?? "/api").replace(/\/+$/, "");
    this.getToken = opts.getToken ?? (() => null);
  }

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (init.body !== undefined && init.body !== null && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    const token = await this.getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);

    const resp = await fetch(`${this.baseUrl}${path}`, { ...init, headers });
    if (!resp.ok) {
      let body: unknown;
      try {
        body = await resp.json();
      } catch {
        body = undefined;
      }
      throw new ApiError(resp.status, `${init.method ?? "GET"} ${path} -> ${resp.status}`, body);
    }
    if (resp.status === 204) return undefined as T;
    return (await resp.json()) as T;
  }

  get<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: "GET" });
  }

  post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
  }
}
