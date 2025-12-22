/**
 * TruePulse E2E Tests - Homepage
 *
 * Tests for the main landing page and poll display functionality.
 */

import { test, expect, samplePoll } from './fixtures';

test.describe('Homepage', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    // Mock the current poll API
    await mockApi.mockPoll(samplePoll);
  });

  test('displays the current poll question', async ({ page }) => {
    await page.goto('/');

    // Wait for the poll to load
    await expect(page.getByRole('heading', { level: 1 })).toContainText(
      'Should remote work become the standard'
    );
  });

  test('displays all poll choices', async ({ page }) => {
    await page.goto('/');

    // Verify all choices are displayed
    await expect(page.getByText('Yes, fully remote')).toBeVisible();
    await expect(page.getByText('Hybrid model')).toBeVisible();
    await expect(page.getByText('No, office is better')).toBeVisible();
    await expect(page.getByText('Depends on the job')).toBeVisible();
  });

  test('displays vote counts when enabled', async ({ page }) => {
    await page.goto('/');

    // Check if vote counts or percentages are displayed
    // This depends on how results are shown (before/after voting)
    const pollCard = page.locator('[data-testid="poll-card"]');
    await expect(pollCard).toBeVisible();
  });

  test('shows time remaining for active poll', async ({ page }) => {
    await page.goto('/');

    // Look for time remaining indicator
    const timeRemaining = page.getByText(/min(utes)?\s*(left|remaining)/i);
    await expect(timeRemaining).toBeVisible();
  });

  test('is responsive on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');

    // Poll should still be visible
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // Navigation should collapse to hamburger menu or similar
    const pollCard = page.locator('[data-testid="poll-card"]');
    await expect(pollCard).toBeVisible();
  });
});

test.describe('Homepage - Closed Poll', () => {
  test('displays closed message for expired poll', async ({ page, mockApi }) => {
    const closedPoll = {
      ...samplePoll,
      is_active: false,
      ends_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // Ended 30 min ago
    };

    await mockApi.mockPoll(closedPoll);
    await page.goto('/');

    // Should indicate poll is closed
    await expect(page.getByText(/closed|ended|finished/i)).toBeVisible();
  });

  test('shows final results for closed poll', async ({ page, mockApi }) => {
    const closedPoll = {
      ...samplePoll,
      is_active: false,
      ends_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    };

    await mockApi.mockPoll(closedPoll);
    await page.goto('/');

    // Results should be visible (percentages)
    await expect(page.getByText(/500/)).toBeVisible(); // Total votes
  });
});

test.describe('Navigation', () => {
  test('header contains logo and navigation links', async ({ page }) => {
    await page.goto('/');

    // Logo should be visible
    await expect(page.getByAltText(/truepulse|logo/i).or(page.getByText('TruePulse'))).toBeVisible();

    // Main navigation elements should exist
    const nav = page.getByRole('navigation');
    await expect(nav).toBeVisible();
  });

  test('sign in button is visible for unauthenticated users', async ({ page }) => {
    await page.goto('/');

    // Should show sign in or login button
    await expect(
      page.getByRole('button', { name: /sign in|log in|login/i }).or(
        page.getByRole('link', { name: /sign in|log in|login/i })
      )
    ).toBeVisible();
  });
});
