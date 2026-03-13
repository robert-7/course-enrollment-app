const { defineConfig, devices } = require('@playwright/test');

const slowMo = Number.parseInt(process.env.PW_SLOWMO || '0', 10);
const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:5000';

module.exports = defineConfig({
  testDir: './e2e',
  timeout: 45 * 1000,
  expect: {
    timeout: 10 * 1000,
  },
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL,
    headless: true,
    launchOptions: {
      slowMo: Number.isNaN(slowMo) ? 0 : slowMo,
    },
    trace: 'on',
    video: 'on',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 1080 },
      },
    },
  ],
});
