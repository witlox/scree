import type { ReactNode } from "react";

import { SessionControls } from "../auth/SessionControls";

/** Top-level information architecture: the product surfaces. Each is a separate
 *  island (ADR-0003); the links use the `?island=` launcher convention so the bundle
 *  is self-navigable (a real htmx deployment can repoint these at its host pages). */
const SECTIONS = [
  { key: "knowledge", label: "Knowledge", href: "/?island=docs" },
  { key: "desk", label: "Service desk", href: "/?island=admin" },
  { key: "portfolio", label: "Portfolio & risk", href: "/?island=portfolio" },
  { key: "admin", label: "Admin", href: "/?island=admin" },
] as const;

export type SectionKey = (typeof SECTIONS)[number]["key"];

/** Responsive app shell (mobile-first): brand + primary nav, then the surface. The
 *  `current` section is marked with aria-current for assistive tech. */
export function AppShell({
  title,
  current,
  children,
}: {
  title: string;
  current?: SectionKey;
  children?: ReactNode;
}) {
  return (
    <div className="app-shell">
      <header className="app-shell__bar">
        <span className="app-shell__brand">Scree</span>
        <nav className="app-shell__nav" aria-label="Primary">
          {SECTIONS.map((s) => (
            <a key={s.key} href={s.href} aria-current={current === s.key ? "page" : undefined}>
              {s.label}
            </a>
          ))}
        </nav>
        <SessionControls />
      </header>
      <main className="app-shell__main" aria-labelledby="shell-title">
        <h1 id="shell-title" className="app-shell__title">
          {title}
        </h1>
        {children}
      </main>
    </div>
  );
}
