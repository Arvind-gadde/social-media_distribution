import { test, expect } from './fixtures';

/**
 * Tier-3 auth flow tests.
 *
 * These are SCAFFOLDED but skipped by default — they require a running backend
 * with a clean test database, plus a seeded test user. Unskip when CI has a
 * dedicated test stack (see tests/e2e/README.md).
 */
test.describe('auth flows @tier-3', () => {
  test.skip(
    !process.env.RUN_TIER_3,
    'Tier-3 auth tests require a dedicated backend test stack; set RUN_TIER_3=1 to enable.'
  );

  test('user can register', async ({ page }) => {
    const unique = Date.now();
    const email = `e2e+register-${unique}@contentflow.dev`;

    await page.goto('/register');

    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/^password$/i).fill('TestPassword123!');

    // Optional fields the form may surface — fill if present.
    const confirm = page.getByLabel(/confirm.*password/i);
    if (await confirm.count()) await confirm.fill('TestPassword123!');

    const name = page.getByLabel(/name/i).first();
    if (await name.count()) await name.fill('E2E Tester');

    await page.getByRole('button', { name: /sign\s*up|register|create/i }).click();

    await expect(page).toHaveURL(/\/(dashboard)?$/);
  });

  test('user can login', async ({ page }) => {
    await page.goto('/login');

    await page.getByLabel(/email/i).fill('e2e+test@contentflow.dev');
    await page.getByLabel(/password/i).fill('TestPassword123!');

    await page.getByRole('button', { name: /sign\s*in|log\s*in/i }).click();

    await expect(page).toHaveURL(/\/(dashboard)?$/);
  });

  test('logged out user is redirected to login on protected route', async ({
    page,
    context,
  }) => {
    // Ensure no auth state leaks in from prior tests.
    await context.clearCookies();
    await page.goto('/dashboard');

    await expect(page).toHaveURL(/\/login(\?.*)?$/);
  });
});
