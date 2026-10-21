import { cpSync } from 'node:fs';
import { resolve } from 'node:path';
import { defineConfig, devices } from '@playwright/test';

// Match the runtime layout assembled by deploy/render/Dockerfile.
cpSync(resolve('.next-release/static'), resolve('.next-release/standalone/.next-release/static'), { recursive: true });
cpSync(resolve('public'), resolve('.next-release/standalone/public'), { recursive: true });

export default defineConfig({
  testDir: './e2e', testMatch: 'public-preview.spec.ts', timeout: 30000, workers: 1,
  use: { baseURL: 'http://127.0.0.1:3127', trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['iPhone 13'], defaultBrowserType: 'chromium' } },
  ],
  webServer: {
    command: 'node .next-release/standalone/server.js',
    url: 'http://127.0.0.1:3127/api/ready', reuseExistingServer: false, timeout: 60000,
    // Build with the ordinary configuration, then enable preview only at startup.
    env: { PUBLIC_PREVIEW: 'true', PUBLIC_WEB_URL: 'https://showcase.example.test', PORT: '3127', HOSTNAME: '127.0.0.1', BACKEND_URL: 'http://127.0.0.1:1' },
  },
});
