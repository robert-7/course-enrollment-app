const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './e2e',
  timeout: 45 * 1000,
  expect: {
    timeout: 10 * 1000,
  },
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL: 'http://127.0.0.1:5000',
    headless: true,
    trace: 'on',
    video: 'on',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
