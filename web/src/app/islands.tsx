import { AdminApp } from "../features/admin/AdminApp";
import { DocsApp } from "../features/docs/DocsApp";
import { PortfolioApp } from "../features/portfolio/PortfolioApp";
import type { IslandRegistry } from "./mountIslands";

/**
 * The island registry. Feature surfaces register their root component here.
 *   - docs: knowledge-management UI (#101) — reader + WYSIWYG editor
 *   - portfolio: portfolio + risk aggregation views (#104)
 *   - admin: internal admin/agent console (#103) — queue, quarantine, orphans, DPO
 * Future: external portal (#102, blocked on #22 scope ratification).
 */
export const islands: IslandRegistry = {
  docs: ({ space }) => <DocsApp space={typeof space === "string" ? space : undefined} />,
  portfolio: () => <PortfolioApp />,
  admin: () => <AdminApp />,
};
