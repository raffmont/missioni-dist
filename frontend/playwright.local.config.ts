import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: 'tests-local',
  workers: 1,
  use: {
    baseURL: 'http://localhost:5173',
    launchOptions: { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH },
  },
});
