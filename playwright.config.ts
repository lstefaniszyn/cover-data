import { defineConfig, devices } from "@playwright/test";
import { config as loadDotenv } from "dotenv";

loadDotenv({ path: ".env.test.dev" });

const useFixtureMarketData = process.env.MARKET_DATA_FIXTURE === "true";
const webServerPort = useFixtureMarketData ? 3001 : 3000;
const webServerEnv: Record<string, string> = Object.fromEntries(
  Object.entries(process.env).filter((entry): entry is [string, string] => entry[1] !== undefined),
);

if (useFixtureMarketData) {
  webServerEnv.MARKET_DATA_FIXTURE = "true";
}

export default defineConfig({
  testDir: "./tests/e2e",
  globalSetup: "./tests/e2e/global-setup.ts",
  timeout: 60_000,
  expect: { timeout: 5_000 },
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [["list"], ["html", { open: "never", outputFolder: "e2e-test-report" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? `http://localhost:${webServerPort}`,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "setup",
      testMatch: /auth\.setup\.ts/,
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "chromium",
      testIgnore: /auth\.setup\.ts/,
      use: { ...devices["Desktop Chrome"], storageState: "auth.json" },
      dependencies: ["setup"],
    },
  ],
  webServer: {
    command: useFixtureMarketData ? "npm run dev -- --port 3001" : "npm run dev",
    env: webServerEnv,
    port: webServerPort,
    reuseExistingServer: useFixtureMarketData ? false : !process.env.CI,
  },
  outputDir: "node_modules/.cache/e2e-test-results",
});
