import type { components } from "../../api/schema";
import { api, ApiError } from "../../api";

// Generated from the gateway OpenAPI schema.
export type TicketSummary = components["schemas"]["TicketSummaryOut"];
export type QuarantineItem = components["schemas"]["QuarantineItemOut"];
export type OrphanReport = components["schemas"]["OrphanReportOut"];
export type ErasureReceipt = components["schemas"]["ErasureReceiptOut"];

export const adminApi = {
  tickets: () => api.get<TicketSummary[]>("/tickets"),
  transition: (id: string, status: string) =>
    api.request<unknown>(`/tickets/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  quarantine: () => api.get<QuarantineItem[]>("/tickets/quarantine"),
  orphans: () => api.get<OrphanReport>("/orphans"),
  erasures: () => api.get<ErasureReceipt[]>("/identities/erasures"),
  erase: (opaqueId: string) =>
    api.request<unknown>(`/identities/${encodeURIComponent(opaqueId)}`, { method: "DELETE" }),
};

export const adminKeys = {
  tickets: ["admin", "tickets"] as const,
  quarantine: ["admin", "quarantine"] as const,
  orphans: ["admin", "orphans"] as const,
  erasures: ["admin", "erasures"] as const,
};

/** True when a query failed because the principal lacks the role (agent/DPO). */
export function isForbidden(error: unknown): boolean {
  return error instanceof ApiError && error.status === 403;
}

/** Legal next transitions for a ticket status (INV-LC-1). */
export function nextTransitions(status: string): Array<{ label: string; status: string }> {
  if (status === "open") return [{ label: "Resolve", status: "resolved" }];
  if (status === "resolved")
    return [
      { label: "Close", status: "closed" },
      { label: "Reopen", status: "open" },
    ];
  return [{ label: "Reopen", status: "open" }]; // closed
}
