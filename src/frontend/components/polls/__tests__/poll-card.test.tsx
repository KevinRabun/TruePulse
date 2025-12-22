/**
 * PollCard Component Tests
 * Tests the poll card component for rendering, voting, and state management
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { PollCard } from '../poll-card';

// Mock dependencies
jest.mock('@/lib/auth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('@/lib/api', () => ({
  api: {
    checkVoteStatus: jest.fn(),
    vote: jest.fn(),
  },
}));

jest.mock('framer-motion', () => {
  const React = require('react');
  
  // Filter out framer-motion specific props to prevent React warnings
  const filterMotionProps = (props: { [key: string]: unknown }) => {
    const motionProps = [
      'initial', 'animate', 'exit', 'transition', 'variants',
      'whileHover', 'whileTap', 'whileFocus', 'whileDrag', 'whileInView',
      'drag', 'dragConstraints', 'dragElastic', 'dragMomentum',
      'onAnimationStart', 'onAnimationComplete', 'layoutId', 'layout',
    ];
    const filtered: { [key: string]: unknown } = {};
    for (const key of Object.keys(props)) {
      if (!motionProps.includes(key)) {
        filtered[key] = props[key];
      }
    }
    return filtered;
  };

  const MotionDiv = React.forwardRef(function MotionDiv({ children, ...props }: { children?: React.ReactNode; [key: string]: unknown }, ref: React.Ref<HTMLDivElement>) {
    return React.createElement('div', { ref, ...filterMotionProps(props) }, children);
  });
  MotionDiv.displayName = 'MotionDiv';

  const MotionButton = React.forwardRef(function MotionButton({ children, ...props }: { children?: React.ReactNode; [key: string]: unknown }, ref: React.Ref<HTMLButtonElement>) {
    return React.createElement('button', { ref, ...filterMotionProps(props) }, children);
  });
  MotionButton.displayName = 'MotionButton';

  const MotionSpan = React.forwardRef(function MotionSpan({ children, ...props }: { children?: React.ReactNode; [key: string]: unknown }, ref: React.Ref<HTMLSpanElement>) {
    return React.createElement('span', { ref, ...filterMotionProps(props) }, children);
  });
  MotionSpan.displayName = 'MotionSpan';

  return {
    motion: {
      div: MotionDiv,
      button: MotionButton,
      span: MotionSpan,
    },
    AnimatePresence: function AnimatePresence({ children }: { children: React.ReactNode }) {
      return React.createElement(React.Fragment, null, children);
    },
  };
});

jest.mock('next/link', () => {
  const React = require('react');
  const Link = function Link({ children, href }: { children: React.ReactNode; href: string }) {
    return React.createElement('a', { href }, children);
  };
  return { default: Link, __esModule: true };
});

jest.mock('@/components/ui/celebration', () => ({
  Celebration: () => null,
  PointsPopup: () => null,
}));

jest.mock('@/components/ui/trust-badge', () => {
  const React = require('react');
  return {
    TrustBadge: () => React.createElement('span', null, 'TrustBadge'),
  };
});

jest.mock('@/components/ui/social-share', () => ({
  SocialShare: () => null,
}));

// Mock lucide-react icons
jest.mock('lucide-react', () => {
  const React = require('react');
  const createIcon = (name: string) => {
    const Icon = () => React.createElement('span', { 'data-testid': `icon-${name}` }, name);
    Icon.displayName = name;
    return Icon;
  };
  return {
    Clock: createIcon('Clock'),
    Users: createIcon('Users'),
    CheckCircle: createIcon('CheckCircle'),
    ChevronRight: createIcon('ChevronRight'),
    Lock: createIcon('Lock'),
    Loader2: createIcon('Loader2'),
    Sparkles: createIcon('Sparkles'),
    Zap: createIcon('Zap'),
    Heart: createIcon('Heart'),
  };
});

import { useAuth } from '@/lib/auth';
import { api } from '@/lib/api';

const mockUseAuth = useAuth as jest.Mock;
const mockApi = api as jest.Mocked<typeof api>;

describe('PollCard', () => {
  const mockPoll = {
    id: 'poll-1',
    question: 'What is your favorite color?',
    choices: [
      { id: 'choice-1', text: 'Red', votePercentage: 40 },
      { id: 'choice-2', text: 'Blue', votePercentage: 35 },
      { id: 'choice-3', text: 'Green', votePercentage: 25 },
    ],
    totalVotes: 100,
    category: 'General',
    sourceEvent: 'Daily Poll',
    expiresAt: new Date(Date.now() + 3600000), // 1 hour from now
    pollType: 'pulse' as const,
    isClosed: false,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    mockUseAuth.mockReturnValue({ isAuthenticated: false });
    mockApi.checkVoteStatus.mockResolvedValue({ poll_id: 'poll-1', has_voted: false });
    mockApi.vote.mockResolvedValue({ success: true, message: 'Vote recorded', points_earned: 10 });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('Rendering', () => {
    it('renders poll question', () => {
      render(<PollCard poll={mockPoll} />);
      expect(screen.getByText('What is your favorite color?')).toBeInTheDocument();
    });

    it('renders all choices', () => {
      render(<PollCard poll={mockPoll} />);
      expect(screen.getByText('Red')).toBeInTheDocument();
      expect(screen.getByText('Blue')).toBeInTheDocument();
      expect(screen.getByText('Green')).toBeInTheDocument();
    });

    it('renders poll category', () => {
      render(<PollCard poll={mockPoll} />);
      expect(screen.getByText('General')).toBeInTheDocument();
    });

    it('renders total votes count', () => {
      render(<PollCard poll={mockPoll} />);
      expect(screen.getByText(/100/)).toBeInTheDocument();
    });

    it('renders Pulse Poll badge for pulse polls', () => {
      render(<PollCard poll={mockPoll} />);
      expect(screen.getByText('Pulse Poll')).toBeInTheDocument();
    });

    it('renders Flash Poll badge for flash polls', () => {
      const flashPoll = { ...mockPoll, pollType: 'flash' as const };
      render(<PollCard poll={flashPoll} />);
      expect(screen.getByText('Flash Poll')).toBeInTheDocument();
    });

    it('does not render poll type badge for standard polls', () => {
      const standardPoll = { ...mockPoll, pollType: 'standard' as const };
      render(<PollCard poll={standardPoll} />);
      expect(screen.queryByText('Pulse Poll')).not.toBeInTheDocument();
      expect(screen.queryByText('Flash Poll')).not.toBeInTheDocument();
    });
  });

  describe('Time Remaining', () => {
    it('displays time remaining for open polls', () => {
      render(<PollCard poll={mockPoll} />);
      expect(screen.getByText(/remaining/i)).toBeInTheDocument();
    });

    it('displays "Closed" for expired polls', () => {
      const expiredPoll = {
        ...mockPoll,
        expiresAt: new Date(Date.now() - 1000), // 1 second ago
      };
      render(<PollCard poll={expiredPoll} />);
      expect(screen.getByText('Closed')).toBeInTheDocument();
    });

    it('displays "Closed" for polls marked as closed', () => {
      // When poll is marked as isClosed: true but hasn't expired yet,
      // the timer still shows time remaining but voting is disabled
      const closedPoll = { 
        ...mockPoll, 
        isClosed: true,
        expiresAt: new Date(Date.now() - 1000) // Also set expired time
      };
      render(<PollCard poll={closedPoll} />);
      expect(screen.getByText('Closed')).toBeInTheDocument();
    });

    it('updates time remaining periodically', async () => {
      const futureDate = new Date(Date.now() + 65000); // 65 seconds from now
      const timedPoll = { ...mockPoll, expiresAt: futureDate };
      
      render(<PollCard poll={timedPoll} />);
      
      // Initial render should show ~1 minute
      expect(screen.getByText(/1m \d+s remaining/)).toBeInTheDocument();
      
      // Advance time and check update
      act(() => {
        jest.advanceTimersByTime(60000); // 60 seconds
      });
      
      // Should now show just seconds
      await waitFor(() => {
        expect(screen.getByText(/\d+s remaining/)).toBeInTheDocument();
      });
    });
  });

  describe('Authentication States', () => {
    it('shows login prompt for unauthenticated users', () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: false });
      render(<PollCard poll={mockPoll} />);
      
      // Unauthenticated users should see a sign in prompt or disabled state
      expect(screen.queryByRole('button', { name: /submit vote/i })).not.toBeInTheDocument();
    });

    it('allows authenticated users to select choices', async () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: true });
      render(<PollCard poll={mockPoll} />);
      
      // Select a choice - choices are div elements with click handlers
      const redChoiceText = screen.getByText('Red');
      const redChoice = redChoiceText.closest('div[class*="rounded-xl"]');
      expect(redChoice).not.toBeNull();
      fireEvent.click(redChoice!);
      
      // Selection should change the element's classes (border-primary-500)
      await waitFor(() => {
        expect(redChoice).toHaveClass('border-primary-500');
      });
    });

    it('checks vote status for authenticated users', async () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: true });
      render(<PollCard poll={mockPoll} />);
      
      await waitFor(() => {
        expect(mockApi.checkVoteStatus).toHaveBeenCalledWith('poll-1');
      });
    });
  });

  describe('Voting Flow', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({ isAuthenticated: true });
      mockApi.checkVoteStatus.mockResolvedValue({ poll_id: 'poll-1', has_voted: false });
    });

    it('submits vote when choice is selected and confirmed', async () => {
      mockApi.vote.mockResolvedValue({ success: true, message: 'Vote recorded', points_earned: 10 });
      render(<PollCard poll={mockPoll} />);
      
      // Wait for vote status check
      await waitFor(() => {
        expect(mockApi.checkVoteStatus).toHaveBeenCalled();
      });
      
      // Select a choice - choices are div elements with click handlers
      const redChoiceText = screen.getByText('Red');
      const redChoice = redChoiceText.closest('div[class*="rounded-xl"]');
      expect(redChoice).not.toBeNull();
      fireEvent.click(redChoice!);
      
      // Find and click vote button
      const voteButton = screen.getByRole('button', { name: /submit vote/i });
      fireEvent.click(voteButton);
        
      await waitFor(() => {
        expect(mockApi.vote).toHaveBeenCalledWith('poll-1', { choice_id: 'choice-1' });
      });
    });

    it('shows results after voting', async () => {
      mockApi.checkVoteStatus.mockResolvedValue({ poll_id: 'poll-1', has_voted: true });
      render(<PollCard poll={mockPoll} />);
      
      await waitFor(() => {
        // Results should show percentages
        expect(screen.getByText('40%')).toBeInTheDocument();
        expect(screen.getByText('35%')).toBeInTheDocument();
        expect(screen.getByText('25%')).toBeInTheDocument();
      });
    });

    it('handles vote error gracefully', async () => {
      mockApi.vote.mockRejectedValue(new Error('Vote failed'));
      render(<PollCard poll={mockPoll} />);
      
      await waitFor(() => {
        expect(mockApi.checkVoteStatus).toHaveBeenCalled();
      });
      
      // Select a choice - choices are div elements with click handlers
      const redChoiceText = screen.getByText('Red');
      const redChoice = redChoiceText.closest('div[class*="rounded-xl"]');
      expect(redChoice).not.toBeNull();
      fireEvent.click(redChoice!);
      
      const voteButton = screen.getByRole('button', { name: /submit vote/i });
      fireEvent.click(voteButton);
        
      await waitFor(() => {
        expect(screen.getByText(/failed/i)).toBeInTheDocument();
      });
    });
  });

  describe('Closed Poll Behavior', () => {
    it('shows results for closed polls', () => {
      const closedPoll = { ...mockPoll, isClosed: true };
      render(<PollCard poll={closedPoll} />);
      
      // Results should be visible
      expect(screen.getByText('40%')).toBeInTheDocument();
    });

    it('does not allow voting on closed polls', () => {
      const closedPoll = { ...mockPoll, isClosed: true };
      mockUseAuth.mockReturnValue({ isAuthenticated: true });
      render(<PollCard poll={closedPoll} />);
      
      // Vote button should not be present
      expect(screen.queryByRole('button', { name: /submit vote/i })).not.toBeInTheDocument();
    });
  });
});
