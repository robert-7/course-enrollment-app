const { test, expect } = require('@playwright/test');

const FAST_INPUT = process.env.PW_FAST_INPUT === '1';

async function typeLikeUser(locator, value) {
  if (FAST_INPUT) {
    await locator.fill(value);
    return;
  }
  await locator.click();
  await locator.pressSequentially(value, { delay: 55 });
}

test('UI walkthrough from TESTING.md', async ({ page }) => {
  const suffix = Date.now();
  const email = `pw${suffix}@e.co`;
  const password = 'secret12';

  // 1. Home page loads.
  await page.goto('/index');
  await expect(page).toHaveURL(/\/index$/);
  await expect(page.getByRole('heading', { name: 'Welcome to Network Operations University.' })).toBeVisible();

  // 2. Courses page loads and shows 5 courses.
  await page.goto('/courses');
  await expect(page).toHaveURL(/\/courses$/);
  await expect(page.locator('table tbody tr')).toHaveCount(5);

  // 3-4. Register a new user and verify redirect home.
  await page.goto('/register');
  await expect(page).toHaveURL(/\/register$/);

  await typeLikeUser(page.locator('#email'), email);
  await typeLikeUser(page.locator('#password'), password);
  await typeLikeUser(page.locator('#password_confirm'), password);
  await typeLikeUser(page.locator('#first_name'), 'Playwright');
  await typeLikeUser(page.locator('#last_name'), 'Tester');
  await page.getByRole('button', { name: 'Register Now' }).click();

  await expect(page).toHaveURL(/\/index$/);

  // 5-6. Login and verify auth nav changes.
  await page.goto('/login');
  await expect(page).toHaveURL(/\/login$/);

  await typeLikeUser(page.locator('#email'), email);
  await typeLikeUser(page.locator('#password'), password);
  await page.getByRole('button', { name: 'Login' }).click();

  await expect(page).toHaveURL(/\/index$/);
  await expect(page.getByRole('link', { name: 'Register' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Login' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Logout' })).toBeVisible();

  // 7-8. Enroll in the first available course.
  await page.goto('/courses');
  await expect(page).toHaveURL(/\/courses$/);
  await page.locator('table tbody tr').first().getByRole('button', { name: 'Enroll' }).click();

  await expect(page).toHaveURL(/\/enrollment$/);
  await expect(page.getByRole('heading', { name: 'Enrollment' })).toBeVisible();

  // 9. Logout and verify logged-out state.
  await page.getByRole('link', { name: 'Logout' }).click();
  await expect(page).toHaveURL(/\/index$/);
  await expect(page.locator('nav').getByRole('link', { name: 'Login' })).toBeVisible();
});
