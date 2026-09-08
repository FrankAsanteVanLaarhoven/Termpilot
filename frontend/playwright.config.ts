import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  testIgnore: process.env.RECORD_DEMO === "1" ? [] : ["**/record-challenge.spec.ts"],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000",
    viewport: { width: 1440, height: 900 },
  },
});
