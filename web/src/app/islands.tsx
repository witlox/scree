import { DocsApp } from "../features/docs/DocsApp";
import type { IslandRegistry } from "./mountIslands";

/**
 * The island registry. Feature surfaces register their root component here.
 *   - docs: knowledge-management UI (#101) — reader + WYSIWYG editor
 * Future: external portal, internal admin/agent, aggregation views.
 */
export const islands: IslandRegistry = {
  docs: ({ space }) => <DocsApp space={typeof space === "string" ? space : undefined} />,
};
