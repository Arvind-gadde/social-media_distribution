/**
 * Production-server route audit:
 * - Unauthenticated user hitting protected routes is redirected.
 * - Public routes serve OK.
 * - Authenticated (cf_session=1) user can reach protected routes.
 * - 404 page renders.
 */
import { test, expect } from '@playwright/test';

const PROTECTED = ['/', '/content', '/studio', '/analytics', '/settings', '/goals'];
const PUBLIC = ['/login', '/register'];

for (const path of PROTECTED) {
  test(`unauth ${path} redirects to /login @auth`, async ({ page, context }) => {
    await context.clearCookies();
    const response = await page.goto(`http://localhost:3000${path}`, { waitUntil: 'commit' });
    expect(response).not.toBeNull();
    expect(page.url()).toContain('/login');
  });
}

for (const path of PUBLIC) {
  test(`public ${path} returns 200 @auth`, async ({ page, context }) => {
    await context.clearCookies();
    const response = await page.goto(`http://localhost:3000${path}`);
    expect(response?.status()).toBe(200);
  });
}

for (const path of ['/', '/content', '/settings']) {
  test(`authed ${path} returns 200 @auth`, async ({ page, context }) => {
    await context.addCookies([
      {
        name: 'cf_session',
        value: '1',
        domain: 'localhost',
        path: '/',
      },
    ]);
    const response = await page.goto(`http://localhost:3000${path}`);
    expect(response?.status()).toBe(200);
  });
}

test('404 page renders with EmptyState @auth', async ({ page, context }) => {
  await context.addCookies([
    { name: 'cf_session', value: '1', domain: 'localhost', path: '/' },
  ]);
  const response = await page.goto('http://localhost:3000/this-does-not-exist');
  expect(response?.status()).toBe(404);
  await expect(page.locator('text=/404|not found/i').first()).toBeVisible();
});
