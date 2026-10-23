import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e', testMatch: 'registration.spec.ts', timeout: 60000, workers: 1,
  globalTeardown: './e2e/auth-teardown.ts',
  use: {
    baseURL: 'http://127.0.0.1:3137', trace: 'retain-on-failure',
    // Exercise the Render IP signature path without trusting browser-supplied XFF.
    extraHTTPHeaders: { 'CF-Connecting-IP': '203.0.113.55' },
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['iPhone 13'], defaultBrowserType: 'chromium' } },
  ],
  webServer: [
    {
      command: process.platform === 'win32' ? '.venv\\Scripts\\python.exe -m tests.auth_browser_server' : '.venv/bin/python -m tests.auth_browser_server',
      cwd: '../backend', url: 'http://127.0.0.1:8137/__auth_test_ready',
      reuseExistingServer: false, timeout: 60000,
    },
    {
      command: 'node scripts/auth-e2e-server.cjs',
      url: 'http://127.0.0.1:3137/login', reuseExistingServer: false, timeout: 120000,
      env: {
        NEXT_DIST_DIR: '.next-auth-e2e', PUBLIC_PREVIEW: 'false', APP_ENV: 'production',
        BACKEND_URL: 'http://127.0.0.1:8137', AUTH_ALLOWED_ORIGINS: 'http://127.0.0.1:3137',
        AUTH_CLIENT_IP_SOURCE: 'render',
        AUTH_PROXY_SECRET: 'auth-browser-fixture-secret-at-least-32-characters',
      },
    },
  ],
});
