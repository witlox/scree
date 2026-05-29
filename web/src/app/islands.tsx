import { DocsApp } from "../features/docs/DocsApp";
import { PortfolioApp } from "../features/portfolio/PortfolioApp";
import type { IslandRegistry } from "./mountIslands";

/**
 * The island registry. Feature surfaces register their root component here.
 *   - docs: knowledge-management UI (#101) — reader + WYSIWYG editor
 *   - portfolio: portfolio + risk aggregation views (#104)
 * Future: external portal, internal admin/agent.
 */
export const islands: IslandRegistry = {
  docs: ({ space }) => <DocsApp space={typeof space === "string" ? space : undefined} />,
  portfolio: () => <PortfolioApp />,
};
