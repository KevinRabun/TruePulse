/**
 * TruePulse E2E Test Fixtures
 *
 * Custom fixtures for authentication, API mocking, etc.
 */

import { test as base, expect } from '@playwright/test';

// Custom fixture types
type TruePulseFixtures = {
  /** Authenticated user context */
  authenticatedPage: ReturnType<typeof base.extend>;
  /** API response interceptors */
  mockApi: {
    mockPoll: (poll: object) => Promise<void>;
    mockUser: (user: object) => Promise<void>;
    mockVoteSuccess: () => Promise<void>;
    mockVoteError: (errorType: string) => Promise<void>;
  };
};

/**
 * Extended test with TruePulse-specific fixtures
 */
export const test = base.extend<TruePulseFixtures>({
  // API mocking helper
  mockApi: async ({ page }, use) => {
    const mockApi = {
      /**
       * Mock the current poll API response
       */
      mockPoll: async (poll: object) => {
        await page.route('**/api/v1/polls/current', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(poll),
          });
        });
      },

      /**
       * Mock the current user API response
       */
      mockUser: async (user: object) => {
        await page.route('**/api/v1/auth/me', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(user),
          });
        });
      },

      /**
       * Mock a successful vote submission
       */
      mockVoteSuccess: async () => {
        await page.route('**/api/v1/secure-votes', async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              success: true,
              vote_id: 'mock-vote-id',
              message: 'Vote recorded successfully',
            }),
          });
        });
      },

      /**
       * Mock a vote error
       */
      mockVoteError: async (errorType: string) => {
        const errorResponses: Record<string, { status: number; body: object }> = {
          already_voted: {
            status: 403,
            body: { error: 'already_voted', message: 'You have already voted on this poll' },
          },
          poll_closed: {
            status: 400,
            body: { error: 'poll_closed', message: 'This poll has ended' },
          },
          rate_limited: {
            status: 429,
            body: { error: 'rate_limited', message: 'Too many requests. Please wait.' },
          },
          unauthorized: {
            status: 401,
            body: { error: 'unauthorized', message: 'Please sign in to vote' },
          },
        };

        const response = errorResponses[errorType] || errorResponses.unauthorized;

        await page.route('**/api/v1/secure-votes', async (route) => {
          await route.fulfill({
            status: response.status,
            contentType: 'application/json',
            body: JSON.stringify(response.body),
          });
        });
      },
    };

    await use(mockApi);
  },
});

export { expect };

/**
 * Sample poll data for testing
 */
export const samplePoll = {
  id: 'test-poll-1',
  question: 'Should remote work become the standard for office jobs?',
  topic: 'Work & Career',
  choices: [
    { id: '1', text: 'Yes, fully remote', vote_count: 150, order: 0 },
    { id: '2', text: 'Hybrid model', vote_count: 200, order: 1 },
    { id: '3', text: 'No, office is better', vote_count: 50, order: 2 },
    { id: '4', text: 'Depends on the job', vote_count: 100, order: 3 },
  ],
  is_active: true,
  starts_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // Started 30 min ago
  ends_at: new Date(Date.now() + 1000 * 60 * 30).toISOString(), // Ends in 30 min
  total_votes: 500,
};

/**
 * Sample authenticated user
 */
export const sampleUser = {
  id: 'test-user-1',
  email: 'test@example.com',
  username: 'testuser',
  is_active: true,
  email_verified: true,
  phone_verified: true,
  created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(), // 30 days ago
};
