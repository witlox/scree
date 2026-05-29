import type { components } from "../../api/schema";
import { api } from "../../api";

// Generated from the gateway OpenAPI schema (response_model on the routes).
export type Portfolio = components["schemas"]["PortfolioOut"];
export type Epic = components["schemas"]["EpicOut"];
export type RiskView = components["schemas"]["RiskViewOut"];

export const portfolioApi = {
  rollup: (cursor = 0) => api.get<Portfolio>(`/planning/portfolio?cursor=${cursor}`),
  risks: () => api.get<RiskView[]>("/risks"),
};

export const portfolioKeys = {
  rollup: (cursor: number) => ["portfolio", cursor] as const,
  risks: ["risks"] as const,
};
