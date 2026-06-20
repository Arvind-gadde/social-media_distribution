import { test, expect, axeScan } from './fixtures';

/**
 * Smoke tests that must always pass.
 *
 * These are the canaries: if these fail, the app is fundamentally broken and
 * deeper test tiers should be skipped.
 */
test.describe('smoke @smoke', () => {
  test('login page renders, matches visual baseline, and is a11y clean @visual', async ({
    page,
  }) => {
    await page.goto('/login');

    // Wait for the primary heading before snapshotting to avoid flake.
    const heading = page.getByRole('heading', { level: 1 });
    await expect(heading).toBeVisible();

    // Accept either the redesigned copy or any variant containing "welcome".
    await expect(heading).toHaveText(/welcome\s*back|sign in|log\s*in/i);

    // Visual regression baseline — first run will create the snapshot.
    await expect(page).toHaveScreenshot('login.png', {
      fullPage: true,
      animations: 'disabled',
    });

    // Accessibility scan — fails on any critical violations.
    await axeScan(page);
  });
});
