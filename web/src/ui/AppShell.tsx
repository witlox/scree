import type { ReactNode } from "react";

/** Responsive layout primitive (mobile-first; widens on larger viewports via
 *  global.css). A surface-agnostic shell — not a feature page. */
export function AppShell({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="app-shell">
      <header className="app-shell__bar">
        <h1 className="app-shell__title">{title}</h1>
      </header>
      <main className="app-shell__main">{children}</main>
    </div>
  );
}
