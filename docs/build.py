#!/usr/bin/env python3
"""Assemble the Scree documentation book from the repo's own sources.

The site is *generated*, not hand-curated: it mirrors `docs/` (narrative + ADRs)
and `specs/` (domain model, invariants, permission model, architecture, fidelity,
findings), renders every `specs/features/*.feature` as a page, and introspects the
running gateway to emit an API reference. The result is written to `site/src/`
with a generated `SUMMARY.md`; `mdbook build` (driven by `book.toml`) renders it.

Run:  python docs/build.py   then   mdbook build
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "site" / "src"


def h1(path: Path, default: str) -> str:
    """First level-1 heading of a markdown file, else the default."""
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return default


def feature_title(text: str, default: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s.lower().startswith("feature:"):
            return s.split(":", 1)[1].strip()
    return default


def copy_tree(rel: str) -> None:
    """Mirror a repo subtree into the book src, preserving relative links."""
    dst = SRC / rel
    shutil.copytree(ROOT / rel, dst, dirs_exist_ok=True)


def render_features() -> list[tuple[str, str]]:
    """Wrap each .feature in a gherkin code fence so mdBook renders it.

    Returns (title, src-relative-path) pairs for the SUMMARY, sorted by title.
    """
    out = SRC / "features"
    out.mkdir(parents=True, exist_ok=True)
    pages: list[tuple[str, str]] = []
    for feat in sorted((ROOT / "specs" / "features").glob("*.feature")):
        text = feat.read_text(encoding="utf-8")
        title = feature_title(text, feat.stem.replace("_", " ").title())
        page = out / f"{feat.stem}.md"
        page.write_text(f"# {title}\n\n```gherkin\n{text}\n```\n", encoding="utf-8")
        pages.append((title, f"features/{feat.stem}.md"))
    return sorted(pages)


def render_api_reference() -> str:
    """Introspect the dev gateway's route table into a markdown reference."""
    os.environ.setdefault("SCREE_DEV", "1")
    sys.path.insert(0, str(ROOT / "api"))
    from starlette.routing import Mount  # imported lazily; only needed here

    from scree.asgi import build_app

    def walk(routes, prefix: str = ""):
        items = []
        for r in routes:
            if isinstance(r, Mount):
                try:
                    items += walk(r.routes, prefix + r.path)
                except Exception:
                    pass  # opaque sub-app (e.g. StaticFiles) — nothing to enumerate
                continue
            methods = sorted(m for m in (getattr(r, "methods", None) or []) if m not in {"HEAD", "OPTIONS"})
            path = getattr(r, "path", "")
            if not methods or not path or path.endswith("openapi.json"):
                continue  # skip the framework's own schema endpoint
            summary = getattr(r, "summary", None)
            if not summary:
                doc = getattr(getattr(r, "endpoint", None), "__doc__", None)
                summary = doc.strip().splitlines()[0] if doc else (getattr(r, "name", "") or "")
            items.append((prefix + path, ", ".join(methods), summary))
        return items

    rows = sorted(set(walk(build_app().routes)))
    lines = [
        "# API Reference",
        "",
        "Generated from the gateway's route table (`scree.asgi:build_app`). The gateway",
        "is the single enforcement point: every path below is authorized server-side.",
        "",
        "| Method | Path | Summary |",
        "|---|---|---|",
    ]
    for path, methods, summary in rows:
        lines.append(f"| {methods} | `{path}` | {summary.replace('|', '\\|')} |")
    lines.append("")
    return "\n".join(lines)


def build_summary(features: list[tuple[str, str]]) -> str:
    def link(rel: str, title: str | None = None) -> str:
        t = title or h1(ROOT / rel, Path(rel).stem)
        return f"[{t}]({rel})"

    lines: list[str] = ["# Summary", ""]
    # Prefix chapter: the landing / front page (a real introduction, not a
    # build-process artifact).
    lines.append("[Scree](docs/index.md)")
    lines.append("")

    lines.append("# Why Scree")
    lines.append("")
    lines.append(f"- {link('docs/why.md', 'The case for Scree')}")
    lines.append("")

    lines.append("# User Guide")
    lines.append("")
    for rel, title in [
        ("docs/usage/getting-started.md", "Getting Started"),
        ("docs/usage/customer-portal.md", "Customer Portal"),
        ("docs/usage/knowledge.md", "Knowledge"),
        ("docs/usage/portfolio-and-risk.md", "Portfolio & Risk"),
        ("docs/usage/agent-console.md", "Agent Console"),
    ]:
        lines.append(f"- {link(rel, title)}")
    lines.append("")

    lines.append("# Operating Scree")
    lines.append("")
    lines.append(f"- {link('docs/operator-guide.md', 'Operator Guide')}")
    lines.append(f"- {link('docs/glossary.md', 'Glossary')}")
    lines.append("")

    lines.append("# Domain & Specification")
    lines.append("")
    for rel in [
        "specs/domain-model.md",
        "specs/ubiquitous-language.md",
        "specs/invariants.md",
        "specs/permission-model.md",
        "specs/assumptions.md",
        "specs/failure-modes.md",
        "specs/cross-context/interactions.md",
    ]:
        lines.append(f"- {link(rel)}")
    lines.append(f"- {link('specs/frontmatter-schemas/README.md', 'Frontmatter Schemas')}")
    for rel in ["specs/frontmatter-schemas/doc.md", "specs/frontmatter-schemas/risk.md", "specs/frontmatter-schemas/ticket.md"]:
        lines.append(f"  - {link(rel)}")
    lines.append("")

    lines.append("# Behaviour (Features)")
    lines.append("")
    for title, rel in features:
        lines.append(f"- [{title}]({rel})")
    lines.append("")

    lines.append("# Architecture")
    lines.append("")
    for rel in [
        "specs/architecture/context-graph.md",
        "specs/architecture/module-graph.md",
        "specs/architecture/permission-enforcement-map.md",
        "specs/architecture/indexer-design.md",
        "specs/architecture/data-structures.md",
        "specs/architecture/error-taxonomy.md",
        "specs/architecture/deployment-topology.md",
    ]:
        lines.append(f"- {link(rel)}")
    lines.append("")

    lines.append("# API")
    lines.append("")
    lines.append("- [API Reference](api-reference.md)")
    lines.append("")

    lines.append("# Decisions (ADRs)")
    lines.append("")
    for adr in sorted((ROOT / "docs" / "decisions").glob("[0-9]*.md")):
        lines.append(f"- {link(f'docs/decisions/{adr.name}')}")
    lines.append("")

    lines.append("# Quality & Assurance")
    lines.append("")
    lines.append(f"- {link('specs/fidelity/INDEX.md', 'Fidelity Index')}")
    for rel in ["specs/fidelity/coverage.md", "specs/fidelity/frontend.md", "specs/fidelity/boundaries.md", "specs/fidelity/enforcement.md", "specs/fidelity/gaps.md"]:
        lines.append(f"  - {link(rel)}")
    lines.append(f"- {link('specs/integration/readiness.md', 'Integration Readiness')}")
    lines.append(f"- {link('specs/findings/INDEX.md', 'Findings Ledger')}")
    for found in sorted((ROOT / "specs" / "findings").glob("*.md")):
        if found.name == "INDEX.md":
            continue
        lines.append(f"  - {link(f'specs/findings/{found.name}')}")
    lines.append("")

    lines.append("# Background")
    lines.append("")
    lines.append(f"- {link('docs/overview.md', 'Stakeholder design summary')}")
    lines.append(f"- {link('docs/PROPOSAL.md')}")
    lines.append(f"- {link('docs/spike-report.md')}")
    for rel in [
        "docs/analysis/design-conversation.md",
        "docs/analysis/design-decisions.md",
        "docs/analysis/prior-art.md",
        "docs/analysis/open-questions.md",
        "docs/analysis/resolved-questions.md",
    ]:
        lines.append(f"- {link(rel)}")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    if SRC.exists():
        shutil.rmtree(SRC)
    SRC.mkdir(parents=True)

    copy_tree("specs")
    copy_tree("docs")
    # The generator and its own outputs are not book pages.
    (SRC / "docs" / "build.py").unlink(missing_ok=True)
    (SRC / "docs" / "SUMMARY.md").unlink(missing_ok=True)

    features = render_features()
    (SRC / "api-reference.md").write_text(render_api_reference(), encoding="utf-8")
    (SRC / "SUMMARY.md").write_text(build_summary(features), encoding="utf-8")
    print(f"docs: wrote {SRC} ({len(features)} feature pages)")


if __name__ == "__main__":
    main()
