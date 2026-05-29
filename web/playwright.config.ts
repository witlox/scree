import { defineConfig, devices } from "@playwright/test";

/**
 * @e2e harness for the BDD journeys (guidelines/typescript.md). Serves the app via
 * the Vite dev server — which also serves e2e/host.html, the page that mounts a single
 * feature island so a real surface can be driven (the htmx host pages live in GitLab,
 * out of this repo). The API is replaced per-test by Playwright route mocks, so no
 * gateway is needed. Drives a desktop and a mobile viewport — the client must work on
 * both. Not part of `pnpm test` (vitest); runs in the @e2e tier.
 */
export default defineConfig({
  testDir: "e2e",
  use: { baseURL: "http://localhost:4173" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: {
    command: "pnpm exec vite --port 4173 --strictPort",
    port: 4173,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
