/**
 * One-shot visual review across the headline routes.
 * Captures desktop + mobile screenshots for human review.
 * Tagged @review so it's opt-in via --grep.
 */
import { test, expect } from '@playwright/test';

const ROUTES: Array<{ path: string; name: string; waitFor?: string }> = [
  { path: '/login', name: 'login' },
  { path: '/register', name: 'register' },
  { path: '/playground', name: 'playground' },
  { path: '/', name: 'home', waitFor: 'http://localhost:3000/login' }, // unauth redirect
];

for (const route of ROUTES) {
  test(`${route.name} renders @review @visual`, async ({ page }) => {
    await page.goto(`http://localhost:3000${route.path}`);
    await page.waitForLoadState('networkidle').catch(() => {});
    // Give animations 600ms to settle, fonts to swap in
    await page.waitForTimeout(600);
    await expect(page).toHaveScreenshot(`${route.name}.png`, {
      fullPage: true,
      maxDiffPixelRatio: 0.02,
    });
  });
}
