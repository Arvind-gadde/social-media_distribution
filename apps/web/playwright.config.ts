import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for ContentFlow web app.
 *
 * Run from repo root or from apps/web:
 *   pnpm --filter @contentflow/web test:e2e
 *
 * Visual regression baselines live in tests/visual/ — see tests/visual/README.md.
 */
export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : 4,
  reporter: [['html', { open: 'never' }], ['list']],
  fullyParallel: true,
  forbidOnly: !!process.env.CI,

  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  expect: {
    toHaveScreenshot: {
      threshold: 0.02,
      maxDiffPixelRatio: 0.01,
    },
  },

  projects: [
    {
      name: 'chromium-desktop',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 900 },
      },
    },
    {
      name: 'chromium-mobile',
      use: {
        ...devices['iPhone 13'],
      },
    },
  ],

  webServer: {
    command: 'pnpm dev',
    port: 3000,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
