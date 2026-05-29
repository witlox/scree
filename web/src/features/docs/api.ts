import { api, ApiError } from "../../api";

// The gateway returns plain dicts (no response_model), so the generated OpenAPI
// types for these endpoints are untyped. These domain interfaces mirror the backend
// shapes; replace them with generated types once the gateway adds response_models
// (tracked separately). Anchored to specs/ubiquitous-language.md.
export interface DocSummary {
  id: string;
  title: string;
  space: string;
}

export interface DocDetail extends DocSummary {
  body: string;
  schema_version: number;
  path: string | null;
  rev: string | null;
  created: string | null;
  updated: string | null;
}

export interface DocVersion {
  rev: string;
  author: string;
  date: string;
  message: string;
}

export interface WriteResult {
  id: string;
  path: string;
  space: string;
  rev: string;
}

export const docsApi = {
  list: () => api.get<DocSummary[]>("/docs"),
  get: (id: string) => api.get<DocDetail>(`/docs/${encodeURIComponent(id)}`),
  versions: (id: string) => api.get<DocVersion[]>(`/docs/${encodeURIComponent(id)}/versions`),
  write: (body: { path: string; content: string; base_rev?: string | null }) =>
    api.post<WriteResult>("/docs", body),
};

export const docsKeys = {
  list: ["docs"] as const,
  detail: (id: string) => ["docs", id] as const,
  versions: (id: string) => ["docs", id, "versions"] as const,
};

/** Rebuild full markdown (frontmatter + body) for a write. Title/space are emitted as
 *  JSON scalars (valid YAML) so punctuation can't break the frontmatter block. */
export function buildDocContent(d: {
  id: string;
  schema_version: number;
  title: string;
  space: string;
  body: string;
}): string {
  const frontmatter = [
    "---",
    `id: ${d.id}`,
    "kind: doc",
    `schema_version: ${d.schema_version}`,
    `title: ${JSON.stringify(d.title)}`,
    `space: ${JSON.stringify(d.space)}`,
    "---",
  ].join("\n");
  return `${frontmatter}\n${d.body}\n`;
}

export type WriteFailure = "governed" | "conflict" | "forbidden" | "invalid" | "other";

/** Map a write error to a UI category. The gateway's central handler returns
 *  {detail: <ExceptionName>} (e.g. MRRequired, Conflict). */
export function classifyWriteError(e: unknown): WriteFailure {
  if (!(e instanceof ApiError)) return "other";
  const detail = (e.body as { detail?: string } | undefined)?.detail ?? "";
  if (e.status === 409 && detail === "MRRequired") return "governed";
  if (e.status === 409) return "conflict"; // Conflict / GitWriteError
  if (e.status === 403) return "forbidden";
  if (e.status === 422) return "invalid";
  return "other";
}
