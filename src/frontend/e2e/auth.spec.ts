/**
 * TruePulse E2E Tests - Authentication Flow
 *
 * Tests for user authentication including:
 * - Sign in
 * - Sign up
 * - Sign out
 * - Password reset
 */

import { test, expect } from './fixtures';

test.describe('Authentication - Sign In', () => {
  test('displays sign in form', async ({ page }) => {
    await page.goto('/auth/signin');

    // Form elements should be present
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in|log in/i })).toBeVisible();
  });

  test('shows validation error for invalid email', async ({ page }) => {
    await page.goto('/auth/signin');

    // Enter invalid email
    await page.getByLabel(/email/i).fill('notanemail');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /sign in|log in/i }).click();

    // Should show validation error
    await expect(page.getByText(/invalid email|valid email/i)).toBeVisible();
  });

  test('shows error for incorrect credentials', async ({ page }) => {
    // Mock failed login
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'invalid_credentials',
          message: 'Invalid email or password',
        }),
      });
    });

    await page.goto('/auth/signin');

    await page.getByLabel(/email/i).fill('test@example.com');
    await page.getByLabel(/password/i).fill('wrongpassword');
    await page.getByRole('button', { name: /sign in|log in/i }).click();

    // Should show error message
    await expect(page.getByText(/invalid|incorrect|wrong/i)).toBeVisible();
  });

  test('redirects to home after successful login', async ({ page }) => {
    // Mock successful login
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'mock-jwt-token',
          token_type: 'bearer',
          user: {
            id: 'user-1',
            email: 'test@example.com',
            username: 'testuser',
          },
        }),
      });
    });

    await page.goto('/auth/signin');

    await page.getByLabel(/email/i).fill('test@example.com');
    await page.getByLabel(/password/i).fill('correctpassword');
    await page.getByRole('button', { name: /sign in|log in/i }).click();

    // Should redirect to home
    await page.waitForURL('/');
    await expect(page).toHaveURL('/');
  });

  test('has link to sign up page', async ({ page }) => {
    await page.goto('/auth/signin');

    const signUpLink = page.getByRole('link', { name: /sign up|create account|register/i });
    await expect(signUpLink).toBeVisible();
    await signUpLink.click();

    await expect(page).toHaveURL(/signup|register/);
  });

  test('has link to forgot password', async ({ page }) => {
    await page.goto('/auth/signin');

    const forgotLink = page.getByRole('link', { name: /forgot|reset/i });
    await expect(forgotLink).toBeVisible();
  });
});

test.describe('Authentication - Sign Up', () => {
  test('displays sign up form', async ({ page }) => {
    await page.goto('/auth/signup');

    // Form elements should be present
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i).first()).toBeVisible();
    await expect(page.getByLabel(/username/i).or(page.getByLabel(/name/i))).toBeVisible();
    await expect(page.getByRole('button', { name: /sign up|create|register/i })).toBeVisible();
  });

  test('validates password strength', async ({ page }) => {
    await page.goto('/auth/signup');

    // Enter weak password
    const passwordField = page.getByLabel(/^password$/i).or(page.getByLabel(/password/i).first());
    await passwordField.fill('weak');

    // Tab away to trigger validation
    await page.getByLabel(/email/i).focus();

    // Should show password requirements
    await expect(
      page.getByText(/characters|strength|weak|strong/i)
    ).toBeVisible({ timeout: 3000 });
  });

  test('validates matching passwords', async ({ page }) => {
    await page.goto('/auth/signup');

    // Fill passwords that don't match
    await page.getByLabel(/^password$/i).or(page.getByLabel(/password/i).first()).fill('Password123!');
    await page.getByLabel(/confirm/i).fill('DifferentPassword123!');

    // Submit form
    await page.getByRole('button', { name: /sign up|create|register/i }).click();

    // Should show mismatch error
    await expect(page.getByText(/match|same/i)).toBeVisible();
  });

  test('shows error for existing email', async ({ page }) => {
    // Mock email already exists error
    await page.route('**/api/v1/auth/register', async (route) => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'email_exists',
          message: 'An account with this email already exists',
        }),
      });
    });

    await page.goto('/auth/signup');

    await page.getByLabel(/email/i).fill('existing@example.com');
    await page.getByLabel(/username/i).or(page.getByLabel(/name/i)).fill('newuser');
    await page.getByLabel(/^password$/i).or(page.getByLabel(/password/i).first()).fill('Password123!');
    
    const confirmPassword = page.getByLabel(/confirm/i);
    if (await confirmPassword.isVisible()) {
      await confirmPassword.fill('Password123!');
    }
    
    await page.getByRole('button', { name: /sign up|create|register/i }).click();

    // Should show error
    await expect(page.getByText(/exists|already|taken/i)).toBeVisible();
  });
});

test.describe('Authentication - Sign Out', () => {
  test('can sign out when logged in', async ({ page }) => {
    // Setup authenticated state
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'user-1',
          email: 'test@example.com',
          username: 'testuser',
        }),
      });
    });

    await page.route('**/api/v1/auth/logout', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Logged out successfully' }),
      });
    });

    await page.goto('/');

    // Click user menu or sign out button
    const userMenu = page.getByTestId('user-menu').or(page.getByRole('button', { name: /testuser|profile|account/i }));
    
    if (await userMenu.isVisible()) {
      await userMenu.click();
    }

    const signOutButton = page.getByRole('button', { name: /sign out|log out|logout/i }).or(
      page.getByRole('menuitem', { name: /sign out|log out/i })
    );
    
    await signOutButton.click();

    // Should show sign in button (logged out state)
    await expect(
      page.getByRole('button', { name: /sign in/i }).or(
        page.getByRole('link', { name: /sign in/i })
      )
    ).toBeVisible();
  });
});

test.describe('Authentication - Password Reset', () => {
  test('can request password reset', async ({ page }) => {
    // Mock password reset request
    await page.route('**/api/v1/auth/forgot-password', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Reset email sent' }),
      });
    });

    await page.goto('/auth/forgot-password');

    await page.getByLabel(/email/i).fill('test@example.com');
    await page.getByRole('button', { name: /send|reset|submit/i }).click();

    // Should show success message
    await expect(page.getByText(/sent|check|email/i)).toBeVisible();
  });
});

test.describe('Protected Routes', () => {
  test('redirects to login when accessing protected route', async ({ page }) => {
    // Mock unauthenticated state
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'unauthorized' }),
      });
    });

    // Try to access a protected route (e.g., profile)
    await page.goto('/profile');

    // Should redirect to sign in
    await page.waitForURL(/signin|login/);
  });
});
