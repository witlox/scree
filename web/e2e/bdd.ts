/**
 * A tiny, dependency-free Gherkin runner for the @e2e tier. It reads the SAME
 * canonical feature files the @api tier binds (../../specs/features), so the browser
 * journeys execute the analyst's scenarios directly — no hand-copied duplicate that
 * could drift. (We avoid `playwright-bdd` only because adding it would require
 * regenerating the pnpm lockfile; this loader covers the small @e2e subset.)
 */
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { test, type Page } from "@playwright/test";

const HERE = dirname(fileURLToPath(import.meta.url));
export const FEATURES_DIR = resolve(HERE, "..", "..", "specs", "features");

export interface Scenario {
  name: string;
  tags: string[];
  steps: string[];
}

export function loadScenarios(file: string, tag: string): Scenario[] {
  const lines = readFileSync(resolve(FEATURES_DIR, file), "utf-8").split("\n");
  const scenarios: Scenario[] = [];
  let featureTags: string[] = [];
  let pending: string[] = [];
  let background: string[] = [];
  let current: Scenario | null = null;
  let inBackground = false;

  for (const raw of lines) {
    const line = raw.trim();
    if (line === "" || line.startsWith("#")) continue;
    if (line.startsWith("@")) {
      pending = line.split(/\s+/).map((t) => t.replace(/^@/, ""));
      continue;
    }
    if (line.startsWith("Feature:")) {
      featureTags = pending;
      pending = [];
      continue;
    }
    if (line.startsWith("Background:")) {
      inBackground = true;
      background = [];
      continue;
    }
    if (line.startsWith("Scenario:") || line.startsWith("Scenario Outline:")) {
      inBackground = false;
      current = { name: line.replace(/^Scenario( Outline)?:\s*/, ""), tags: [...featureTags, ...pending], steps: [...background] };
      pending = [];
      scenarios.push(current);
      continue;
    }
    const m = /^(Given|When|Then|And|But)\s+(.*)$/.exec(line);
    if (m) {
      if (inBackground) background.push(m[2]);
      else if (current) current.steps.push(m[2]);
    }
  }
  return scenarios.filter((s) => s.tags.includes(tag));
}

export interface Ctx {
  page: Page;
  [key: string]: unknown;
}

type StepFn = (ctx: Ctx, ...args: string[]) => Promise<void> | void;

export class Steps {
  private bindings: { re: RegExp; fn: StepFn }[] = [];

  def(pattern: string, fn: StepFn): this {
    const source = pattern.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\\\{(\w+)\\\}/g, '([^"]+)');
    this.bindings.push({ re: new RegExp(`^${source}$`), fn });
    return this;
  }

  async run(ctx: Ctx, text: string): Promise<void> {
    for (const b of this.bindings) {
      const m = b.re.exec(text);
      if (m) {
        await b.fn(ctx, ...m.slice(1));
        return;
      }
    }
    throw new Error(`No @e2e step definition for: ${text}`);
  }
}

export interface RunOptions {
  setup?: (ctx: Ctx) => Promise<void> | void;
  fixme?: (name: string) => string | undefined;
}

export function runFeature(file: string, tag: string, steps: Steps, opts: RunOptions = {}): void {
  for (const sc of loadScenarios(file, tag)) {
    test(sc.name, async ({ page }) => {
      const reason = opts.fixme?.(sc.name);
      test.fixme(Boolean(reason), reason ?? "");
      const ctx: Ctx = { page };
      if (opts.setup) await opts.setup(ctx);
      for (const step of sc.steps) await steps.run(ctx, step);
    });
  }
}
