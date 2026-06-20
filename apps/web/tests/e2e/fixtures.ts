import { test as base, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

/**
 * Test fixtures and helpers for ContentFlow E2E tests.
 *
 * - `authenticatedPage`: a Page already signed in as the configured test user.
 * - `axeScan(page)`: runs axe-core against the page and fails on critical violations.
 */

const API_BASE_URL =
  process.env.PLAYWRIGHT_API_BASE_URL ?? 'http://localhost:8000';
const TEST_USER_EMAIL =
  process.env.PLAYWRIGHT_TEST_EMAIL ?? 'e2e+test@contentflow.dev';
const TEST_USER_PASSWORD =
  process.env.PLAYWRIGHT_TEST_PASSWORD ?? 'TestPassword123!';

interface AuthFixtures {
  authenticatedPage: Page;
}

export const test = base.extend<AuthFixtures>({
  authenticatedPage: async ({ page, baseURL }, use) => {
    // Hit the backend API directly to obtain a session token.
    const response = await page.request.post(
      `${API_BASE_URL}/api/v1/auth/login`,
      {
        data: {
          email: TEST_USER_EMAIL,
          password: TEST_USER_PASSWORD,
        },
        failOnStatusCode: false,
      }
    );

    let accessToken: string | undefined;
    if (response.ok()) {
      const body = (await response.json()) as {
        access_token?: string;
        token?: string;
      };
      accessToken = body.access_token ?? body.token;
    }

    if (!accessToken) {
      // Fail loudly so the developer knows the backend or seed user is missing.
      throw new Error(
        `authenticatedPage fixture: failed to log in test user via ${API_BASE_URL}/api/v1/auth/login (status ${response.status()}). ` +
          `Ensure the backend is running and the seed user exists, or override PLAYWRIGHT_TEST_EMAIL/PASSWORD.`
      );
    }

    // Mirror what the app does post-login: cookie + localStorage.
    const url = new URL(baseURL ?? 'http://localhost:3000');
    await page.context().addCookies([
      {
        name: 'cf_session',
        value: accessToken,
        domain: url.hostname,
        path: '/',
        httpOnly: false,
        secure: false,
        sameSite: 'Lax',
      },
    ]);

    // Visit the app once so we can seed localStorage.
    await page.goto('/');
    await page.evaluate((token) => {
      window.localStorage.setItem('access_token', token);
    }, accessToken);

    await use(page);
  },
});

export { expect };

/**
 * Run axe-core against the current page.
 *
 * Fails the test if any violation has `impact === 'critical'`.
 * Returns the raw axe results so individual tests can perform further assertions.
 */
export async function axeScan(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();

  const critical = results.violations.filter((v) => v.impact === 'critical');
  if (critical.length > 0) {
    const summary = critical
      .map(
        (v) =>
          `- [${v.id}] ${v.help} (${v.nodes.length} node(s)) -> ${v.helpUrl}`
      )
      .join('\n');
    throw new Error(
      `axe found ${critical.length} critical accessibility violation(s):\n${summary}`
    );
  }

  return results;
}
