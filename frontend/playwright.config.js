import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  fullyParallel: false,
  timeout: 60_000,
  use: {
    baseURL: "http://127.0.0.1:5174",
    timezoneId: "Asia/Tokyo",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    launchOptions: process.env.SPACEPORT_CHROME
      ? { executablePath: process.env.SPACEPORT_CHROME }
      : {},
  },
  webServer: [
    {
      command: "../.venv/bin/python e2e/backend.py",
      url: "http://127.0.0.1:8011/api/ships",
      reuseExistingServer: false,
    },
    {
      command:
        "node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5174 --strictPort",
      url: "http://127.0.0.1:5174",
      env: { SPACEPORT_API_URL: "http://127.0.0.1:8011" },
      reuseExistingServer: false,
    },
  ],
});
