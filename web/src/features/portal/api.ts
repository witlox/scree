import type { components } from "../../api/schema";
import { api } from "../../api";

// Generated from the gateway OpenAPI schema.
export type TicketSummary = components["schemas"]["TicketSummaryOut"];
export type TicketDetail = components["schemas"]["TicketDetailOut"];
export type Comment = components["schemas"]["CommentOut"];
export type Attachment = components["schemas"]["AttachmentOut"];
export type CommunityHit = components["schemas"]["CommunityHitOut"];
export type Preference = components["schemas"]["PreferenceOut"];
export type TicketCreated = components["schemas"]["TicketCreatedOut"];

const id = (s: string) => encodeURIComponent(s);

export const portalApi = {
  myTickets: () => api.get<TicketSummary[]>("/tickets"),
  submit: (body: string) => api.post<TicketCreated>("/tickets", { origin: "web", body }),
  ticket: (tid: string) => api.get<TicketDetail>(`/tickets/${id(tid)}`),
  comments: (tid: string) => api.get<Comment[]>(`/tickets/${id(tid)}/comments`),
  reply: (tid: string, body: string) => api.post<Comment>(`/tickets/${id(tid)}/comments`, { body }),
  attach: (tid: string, filename: string, content: string) =>
    api.post<Attachment>(`/tickets/${id(tid)}/attachments`, { filename, content }),
  attachments: (tid: string) => api.get<Attachment[]>(`/tickets/${id(tid)}/attachments`),
  search: (q: string) => api.get<CommunityHit[]>(`/community/search?q=${encodeURIComponent(q)}`),
  getPref: () => api.get<Preference>("/portal/preferences"),
  setPref: (preference: string) =>
    api.request<Preference>("/portal/preferences", { method: "PUT", body: JSON.stringify({ preference }) }),
};

export const portalKeys = {
  myTickets: ["portal", "tickets"] as const,
  ticket: (tid: string) => ["portal", "ticket", tid] as const,
  comments: (tid: string) => ["portal", "comments", tid] as const,
  attachments: (tid: string) => ["portal", "attachments", tid] as const,
  search: (q: string) => ["portal", "search", q] as const,
  pref: ["portal", "pref"] as const,
};
