import type { IslandRegistry } from "./mountIslands";

/**
 * The island registry. Empty by design at the foundation stage — feature surfaces
 * register their root components here as they are built:
 *   - docs WYSIWYG editor (React island; reader is htmx)
 *   - external customer portal
 *   - internal admin / agent queues + dashboards
 *   - portfolio / risk aggregation views
 */
export const islands: IslandRegistry = {};
