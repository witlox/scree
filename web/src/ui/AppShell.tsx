import type { ReactNode } from "react";

/** Top-level information architecture: the four product surfaces. Links resolve to
 *  their (server-routed) pages; surfaces are separate islands per ADR-0003. */
const SECTIONS = [
  { key: "knowledge", label: "Knowledge", href: "/docs" },
  { key: "desk", label: "Service desk", href: "/desk" },
  { key: "portfolio", label: "Portfolio & risk", href: "/portfolio" },
  { key: "admin", label: "Admin", href: "/admin" },
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
