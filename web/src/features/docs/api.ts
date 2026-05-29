import type { components } from "../../api/schema";
import { api, ApiError } from "../../api";

// Types are GENERATED from the gateway OpenAPI schema (response_model on the routes),
// never hand-written. See .claude/coding/typescript.md.
export type DocSummary = components["schemas"]["DocSummaryOut"];
export type DocDetail = components["schemas"]["DocDetailOut"];
export type DocVersion = components["schemas"]["DocVersionOut"];
export type WriteResult = components["schemas"]["DocWriteOut"];

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
