/**
 * Tests for VerificationBanner component
 */
import { render, screen } from '@testing-library/react';
import { VerificationBanner } from '../VerificationBanner';

// Mock the auth hook
const mockUseAuth = jest.fn();
jest.mock('@/lib/auth', () => ({
  useAuth: () => mockUseAuth(),
}));

describe('VerificationBanner', () => {
  beforeEach(() => {
    mockUseAuth.mockReset();
  });

  it('does not render when user is not authenticated', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      user: null,
    });

    const { container } = render(<VerificationBanner />);
    expect(container.firstChild).toBeNull();
  });

  it('does not render when user is fully verified', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: {
        id: 'user-123',
        email_verified: true,
        phone_verified: true,
      },
    });

    const { container } = render(<VerificationBanner />);
    expect(container.firstChild).toBeNull();
  });

  it('renders banner when email is not verified', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: {
        id: 'user-123',
        email_verified: false,
        phone_verified: true,
      },
    });

    render(<VerificationBanner />);
    expect(screen.getByText(/verify/i)).toBeInTheDocument();
  });

  it('renders banner when phone is not verified', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: {
        id: 'user-123',
        email_verified: true,
        phone_verified: false,
      },
    });

    render(<VerificationBanner />);
    expect(screen.getByText(/verify/i)).toBeInTheDocument();
  });
});
