import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e', testMatch: 'platega-payment.spec.ts', timeout: 60000, workers: 1, retries: 0,
  globalTeardown: './e2e/payment-teardown.ts',
  use: { baseURL: 'http://127.0.0.1:3117', trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['iPhone 13'], defaultBrowserType: 'chromium' } },
  ],
  webServer: [
    { command: process.platform === 'win32' ? '.venv\\Scripts\\python.exe -m tests.manual_payment_server' : '.venv/bin/python -m tests.manual_payment_server',
      cwd: '../backend', url: 'http://127.0.0.1:8117/__test_ready', reuseExistingServer: false, timeout: 60000 },
    { command: 'node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port 3117',
      url: 'http://127.0.0.1:3117/login', reuseExistingServer: false, timeout: 120000,
      env: { NEXT_DIST_DIR: '.next-manual-e2e', BACKEND_URL: 'http://127.0.0.1:8117', AUTH_ALLOWED_ORIGINS: 'http://127.0.0.1:3117' } },
  ],
});
