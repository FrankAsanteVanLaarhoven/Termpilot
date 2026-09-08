import { expect, test } from "@playwright/test";

test("home overview opens from the TermPilot mark", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: /Try the demo/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Grok Bot/i })).toBeVisible();
  await page.getByRole("button", { name: /Try the demo/i }).click();
  await expect(page.getByText("What needs your attention today?")).toBeVisible({ timeout: 45_000 });
  await page.getByRole("button", { name: /Review my week/i }).click();
  await expect(page.getByRole("button", { name: /Home/i }).first()).toBeVisible();
  await page.getByRole("button", { name: /Home/i }).first().click();
  await expect(page.getByText("What needs your attention today?")).toBeVisible();
});
