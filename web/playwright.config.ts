import { defineConfig, devices } from "@playwright/test";

/**
 * @e2e harness for the BDD journeys (guidelines/typescript.md). Runs the built app
 * via `vite preview` and drives it across a mobile and a desktop viewport — the
 * client must work on both. Not part of `pnpm test` (vitest); runs in the @e2e tier.
 */
export default defineConfig({
  testDir: "e2e",
  use: { baseURL: "http://localhost:4173" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: {
    command: "pnpm build && pnpm preview --port 4173 --strictPort",
    port: 4173,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
