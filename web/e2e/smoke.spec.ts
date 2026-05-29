import { expect, test } from "@playwright/test";

/** Foundation smoke: the app shell boots and serves on both viewports (the
 *  projects in playwright.config.ts run this on desktop and mobile). Feature
 *  journeys (@e2e Gherkin) land as surfaces are built. */
test("app shell boots", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Scree/);
});
