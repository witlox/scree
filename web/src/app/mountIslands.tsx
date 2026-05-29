import type { ComponentType } from "react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { AuthGate } from "../auth/AuthGate";
import { AuthProvider } from "../auth/AuthProvider";
import { QueryProvider } from "../lib/query/QueryProvider";
import { ErrorBoundary } from "../ui/ErrorBoundary";

/** Names map to the React components that may be mounted as islands. Feature
 *  surfaces (docs editor, portal, admin) add entries in src/app/islands.ts. */
export type IslandRegistry = Record<string, ComponentType<Record<string, unknown>>>;

/**
 * Mount React islands into every `[data-island="name"]` element found under `root`.
 * Props are read from `data-props` (JSON). This is the React/htmx seam: htmx-rendered
 * (or static) pages own the DOM and embed islands; React owns only its island roots
 * (ADR-0003 — one technology per DOM region). Returns the number mounted.
 */
export function mountIslands(registry: IslandRegistry, root: ParentNode = document): number {
  let mounted = 0;
  root.querySelectorAll<HTMLElement>("[data-island]").forEach((el) => {
    const name = el.dataset.island;
    if (!name) return; // empty placeholder
    const Component = registry[name];
    if (!Component) {
      console.warn(`[scree] no island registered for "${name}"`);
      return;
    }
    let props: Record<string, unknown> = {};
    if (el.dataset.props) {
      try {
        props = JSON.parse(el.dataset.props) as Record<string, unknown>;
      } catch {
        console.warn(`[scree] invalid data-props for island "${name}" — ignoring`); // FE-05
      }
    }
    createRoot(el).render(
      <StrictMode>
        <AuthProvider>
          <QueryProvider>
            <AuthGate>
              <ErrorBoundary>
                <Component {...props} />
              </ErrorBoundary>
            </AuthGate>
          </QueryProvider>
        </AuthProvider>
      </StrictMode>,
    );
    mounted += 1;
  });
  return mounted;
}
