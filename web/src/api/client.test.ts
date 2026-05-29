import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiClient, ApiError } from "./client";

function mockFetch(status: number, json: unknown) {
  return vi.fn(
    async (_input: RequestInfo | URL, _init?: RequestInit) =>
      new Response(json === undefined ? null : JSON.stringify(json), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
  );
}

afterEach(() => vi.restoreAllMocks());

describe("ApiClient", () => {
  it("attaches the OIDC bearer and parses JSON", async () => {
    const fetchMock = mockFetch(200, [{ id: "doc-a" }]);
    vi.stubGlobal("fetch", fetchMock);
    const client = new ApiClient({ baseUrl: "/api", getToken: () => "tok-123" });

    const out = await client.get<{ id: string }[]>("/docs");

    expect(out).toEqual([{ id: "doc-a" }]);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/docs");
    expect(new Headers(init!.headers).get("Authorization")).toBe("Bearer tok-123");
  });

  it("omits Authorization when there is no token", async () => {
    const fetchMock = mockFetch(200, {});
    vi.stubGlobal("fetch", fetchMock);
    await new ApiClient().get("/docs");
    const [, init] = fetchMock.mock.calls[0];
    expect(new Headers(init!.headers).has("Authorization")).toBe(false);
  });

  it("throws ApiError on a non-2xx response", async () => {
    vi.stubGlobal("fetch", mockFetch(404, { detail: "NotFound" }));
    const client = new ApiClient();
    await expect(client.get("/tickets/nope")).rejects.toBeInstanceOf(ApiError);
  });
});
