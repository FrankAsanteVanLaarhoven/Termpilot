import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { join } from "node:path";

const demoDir = join(process.cwd(), "..", "docs", "demo");

test.use({
  video: { mode: "on", size: { width: 1440, height: 810 } },
  viewport: { width: 1440, height: 810 },
  launchOptions: { slowMo: 280 },
});

test("record Student Build Challenge demo", async ({ page }) => {
  test.setTimeout(180_000);
  mkdirSync(demoDir, { recursive: true });
  await page.goto("/");
  await expect(page.getByRole("button", { name: /Home/i }).first()).toBeVisible();
  const cookies = page.getByRole("button", { name: /Necessary only/i });
  if (await cookies.isVisible().catch(() => false)) {
    await cookies.click();
  }
  await page.waitForTimeout(900);
  await page.getByLabel("University email").fill("alex.rivera@northbridge.ac.uk");
  await page.getByLabel("Password").fill("rivera-lab-1");
  await page.getByRole("button", { name: /^Sign in$/i }).click();
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: /Enter console|Preparing/i }).click();
  if (await cookies.isVisible().catch(() => false)) {
    await cookies.click();
  }
  await expect(page.getByText("What needs your attention today?")).toBeVisible({ timeout: 45_000 });
  await page.screenshot({ path: join(demoDir, "01-home.png") });
  await page.waitForTimeout(700);

  const ask = page.getByLabel("Ask Grok Bot");
  await ask.click();
  await ask.fill("What should I focus on this week?");
  await page.getByRole("button", { name: /^Ask$/i }).click();
  await expect(page.getByText(/Robotics Lab Report|verified|conflict/i).first()).toBeVisible({
    timeout: 30_000,
  });
  await page.screenshot({ path: join(demoDir, "02-ask-week.png") });
  await page.waitForTimeout(1400);

  await page.getByRole("button", { name: /Review my week/i }).click();
  await expect(page.getByText(/Horizon|Checked|Conflicts|Needs a decision/i).first()).toBeVisible({
    timeout: 20_000,
  });
  await page.screenshot({ path: join(demoDir, "03-my-week.png") });
  await page.waitForTimeout(1600);

  await page.getByRole("button", { name: /Home/i }).first().click();
  await expect(page.getByText("What needs your attention today?")).toBeVisible();
  await page.waitForTimeout(600);

  await page.getByRole("button", { name: /Open messages/i }).click();
  await expect(page.getByText(/Inbox|Urgent|Messages/i).first()).toBeVisible({ timeout: 20_000 });
  await page.screenshot({ path: join(demoDir, "04-messages.png") });
  await page.waitForTimeout(1400);

  await page.getByRole("button", { name: /Show nav/i }).click();
  await page.getByRole("button", { name: /Connected services/i }).click();
  await expect(page.getByText(/GitHub|Jira|One-click connect/i).first()).toBeVisible({
    timeout: 15_000,
  });
  await page.screenshot({ path: join(demoDir, "05-connectors.png") });
  await page.waitForTimeout(1600);

  await page.getByRole("button", { name: /Home/i }).first().click();
  await expect(page.getByText("What needs your attention today?")).toBeVisible();
  await page.waitForTimeout(1000);
});

