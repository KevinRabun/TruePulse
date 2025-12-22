/**
 * TruePulse E2E Tests - Voting Flow
 *
 * Tests for the complete voting experience including:
 * - Vote submission
 * - Error handling
 * - Post-vote experience
 */

import { test, expect, samplePoll, sampleUser } from './fixtures';

test.describe('Voting Flow - Authenticated User', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockPoll(samplePoll);
    await mockApi.mockUser(sampleUser);
  });

  test('can select a poll choice', async ({ page, mockApi }) => {
    await mockApi.mockVoteSuccess();
    await page.goto('/');

    // Click on a choice
    const choice = page.getByText('Hybrid model');
    await choice.click();

    // Choice should be highlighted/selected
    await expect(choice.locator('..')).toHaveClass(/selected|active|chosen/i);
  });

  test('can submit vote successfully', async ({ page, mockApi }) => {
    await mockApi.mockVoteSuccess();
    await page.goto('/');

    // Select a choice
    await page.getByText('Hybrid model').click();

    // Submit vote
    const voteButton = page.getByRole('button', { name: /vote|submit/i });
    await voteButton.click();

    // Should show success feedback
    await expect(
      page.getByText(/thank|success|voted|recorded/i)
    ).toBeVisible({ timeout: 5000 });
  });

  test('shows error when voting fails with already voted', async ({ page, mockApi }) => {
    await mockApi.mockVoteError('already_voted');
    await page.goto('/');

    // Try to vote
    await page.getByText('Hybrid model').click();
    await page.getByRole('button', { name: /vote|submit/i }).click();

    // Should show error message
    await expect(
      page.getByText(/already voted/i)
    ).toBeVisible({ timeout: 5000 });
  });

  test('shows error when rate limited', async ({ page, mockApi }) => {
    await mockApi.mockVoteError('rate_limited');
    await page.goto('/');

    // Try to vote
    await page.getByText('Hybrid model').click();
    await page.getByRole('button', { name: /vote|submit/i }).click();

    // Should show rate limit message
    await expect(
      page.getByText(/too many|wait|slow down/i)
    ).toBeVisible({ timeout: 5000 });
  });

  test('disables vote button while submitting', async ({ page, mockApi }) => {
    // Delay the response to observe the loading state
    await page.route('**/api/v1/secure-votes', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    });

    await page.goto('/');

    // Select and submit
    await page.getByText('Hybrid model').click();
    const voteButton = page.getByRole('button', { name: /vote|submit/i });
    await voteButton.click();

    // Button should be disabled during submission
    await expect(voteButton).toBeDisabled();
  });
});

test.describe('Voting Flow - Unauthenticated User', () => {
  test.beforeEach(async ({ page, mockApi }) => {
    await mockApi.mockPoll(samplePoll);
    // Don't mock user - simulate unauthenticated state
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'unauthorized' }),
      });
    });
  });

  test('prompts sign in when trying to vote', async ({ page, mockApi }) => {
    await mockApi.mockVoteError('unauthorized');
    await page.goto('/');

    // Try to vote
    await page.getByText('Hybrid model').click();

    // Should show sign in prompt or redirect
    await expect(
      page.getByText(/sign in|log in|create account/i).or(
        page.getByRole('button', { name: /sign in/i })
      )
    ).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Post-Vote Experience', () => {
  test('shows updated results after voting', async ({ page, mockApi }) => {
    const updatedPoll = {
      ...samplePoll,
      choices: samplePoll.choices.map((c) =>
        c.id === '2' ? { ...c, vote_count: 201 } : c
      ),
      total_votes: 501,
    };

    await mockApi.mockPoll(samplePoll);
    await mockApi.mockUser(sampleUser);
    await mockApi.mockVoteSuccess();

    await page.goto('/');

    // Vote
    await page.getByText('Hybrid model').click();
    await page.getByRole('button', { name: /vote|submit/i }).click();

    // Wait for success
    await expect(page.getByText(/thank|success|voted/i)).toBeVisible();

    // Mock updated poll for results
    await page.route('**/api/v1/polls/current', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(updatedPoll),
      });
    });

    // Results should update (may need to wait for refresh)
    await expect(page.getByText('501')).toBeVisible({ timeout: 10000 });
  });

  test('cannot vote again after successful vote', async ({ page, mockApi }) => {
    await mockApi.mockPoll(samplePoll);
    await mockApi.mockUser(sampleUser);
    await mockApi.mockVoteSuccess();

    await page.goto('/');

    // First vote
    await page.getByText('Hybrid model').click();
    await page.getByRole('button', { name: /vote|submit/i }).click();
    await expect(page.getByText(/thank|success|voted/i)).toBeVisible();

    // Vote button should be disabled or hidden
    const voteButton = page.getByRole('button', { name: /vote|submit/i });
    const buttonCount = await voteButton.count();

    if (buttonCount > 0) {
      await expect(voteButton).toBeDisabled();
    }
    // Otherwise, button was removed which is also acceptable
  });
});

test.describe('Poll Closed State', () => {
  test('cannot vote on closed poll', async ({ page, mockApi }) => {
    const closedPoll = {
      ...samplePoll,
      is_active: false,
      ends_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    };

    await mockApi.mockPoll(closedPoll);
    await mockApi.mockUser(sampleUser);
    await page.goto('/');

    // Vote button should be disabled or not present
    const voteButton = page.getByRole('button', { name: /vote|submit/i });
    const buttonCount = await voteButton.count();

    if (buttonCount > 0) {
      await expect(voteButton).toBeDisabled();
    }

    // Should show closed message
    await expect(page.getByText(/closed|ended|finished/i)).toBeVisible();
  });
});
