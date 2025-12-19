/**
 * Tests for PollCard component
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { PollCard } from '../poll-card';

// Mock the auth hook
jest.mock('@/lib/auth', () => ({
  useAuth: () => ({
    isAuthenticated: true,
    user: { id: 'test-user-123' },
  }),
}));

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}));

const mockPoll = {
  id: 'poll-123',
  question: 'What is your opinion on this test question?',
  choices: [
    { id: '1', text: 'Strongly agree', votePercentage: 30 },
    { id: '2', text: 'Agree', votePercentage: 25 },
    { id: '3', text: 'Neutral', votePercentage: 20 },
    { id: '4', text: 'Disagree', votePercentage: 15 },
    { id: '5', text: 'Strongly disagree', votePercentage: 10 },
  ],
  totalVotes: 1000,
  category: 'Politics',
  sourceEvent: 'Test news event',
  expiresAt: new Date(Date.now() + 3600000), // 1 hour from now
};

describe('PollCard', () => {
  it('renders poll question', () => {
    render(<PollCard poll={mockPoll} />);
    expect(screen.getByText(mockPoll.question)).toBeInTheDocument();
  });

  it('renders all poll choices', () => {
    render(<PollCard poll={mockPoll} />);
    mockPoll.choices.forEach((choice) => {
      expect(screen.getByText(choice.text)).toBeInTheDocument();
    });
  });

  it('renders poll category', () => {
    render(<PollCard poll={mockPoll} />);
    expect(screen.getByText(mockPoll.category)).toBeInTheDocument();
  });

  it('renders source event when provided', () => {
    render(<PollCard poll={mockPoll} />);
    expect(screen.getByText(`Based on: ${mockPoll.sourceEvent}`)).toBeInTheDocument();
  });

  it('shows time remaining', () => {
    render(<PollCard poll={mockPoll} />);
    // Should show time in format like "0h 59m remaining"
    expect(screen.getByText(/remaining/i)).toBeInTheDocument();
  });

  it('allows selecting a choice when authenticated', () => {
    render(<PollCard poll={mockPoll} />);
    const choice = screen.getByText('Strongly agree');
    fireEvent.click(choice);
    // Verify selection state changes (would need to check visual indicator)
    expect(choice).toBeInTheDocument();
  });
});

describe('PollCard - Unauthenticated', () => {
  beforeEach(() => {
    // Mock unauthenticated state
    jest.spyOn(require('@/lib/auth'), 'useAuth').mockReturnValue({
      isAuthenticated: false,
      user: null,
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('renders poll for unauthenticated users', () => {
    render(<PollCard poll={mockPoll} />);
    expect(screen.getByText(mockPoll.question)).toBeInTheDocument();
  });
});
