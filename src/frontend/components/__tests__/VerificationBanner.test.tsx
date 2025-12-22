/**
 * VerificationBanner Component Tests
 * Tests the verification banner component for email/phone verification status display
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { VerificationBanner } from '../VerificationBanner';

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('VerificationBanner', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading State', () => {
    it('renders nothing while loading', () => {
      mockFetch.mockImplementation(() => new Promise(() => {})); // Never resolves
      const { container } = render(<VerificationBanner />);
      expect(container.firstChild).toBeNull();
    });
  });

  describe('Fully Verified User', () => {
    beforeEach(() => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          email_verified: true,
          phone_verified: true,
        }),
      });
    });

    it('shows verified badge when fully verified', async () => {
      render(<VerificationBanner />);
      
      await waitFor(() => {
        expect(screen.getByText('Verified voter')).toBeInTheDocument();
      });
    });

    it('displays green checkmark icon', async () => {
      render(<VerificationBanner />);
      
      await waitFor(() => {
        const icon = screen.getByText('Verified voter').closest('div')?.querySelector('svg');
        expect(icon).toBeInTheDocument();
      });
    });
  });

  describe('Email Not Verified', () => {
    beforeEach(() => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          email_verified: false,
          phone_verified: true,
        }),
      });
    });

    it('shows warning banner when email not verified', async () => {
      render(<VerificationBanner />);
      
      await waitFor(() => {
        expect(screen.getByText('Verification Required to Vote')).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /verify email/i })).toBeInTheDocument();
      });
    });

    it('displays amber/warning styling', async () => {
      render(<VerificationBanner />);
      
      await waitFor(() => {
        const banner = screen.getByText('Verification Required to Vote').closest('.rounded-lg');
        expect(banner).toHaveClass('border-amber-200', 'bg-amber-50');
      });
    });
  });

  describe('Phone Not Verified', () => {
    beforeEach(() => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          email_verified: true,
          phone_verified: false,
        }),
      });
    });

    it('shows warning banner when phone not verified', async () => {
      render(<VerificationBanner />);
      
      await waitFor(() => {
        expect(screen.getByText('Verification Required to Vote')).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /verify phone/i })).toBeInTheDocument();
      });
    });
  });

  describe('Neither Verified', () => {
    beforeEach(() => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          email_verified: false,
          phone_verified: false,
        }),
      });
    });

    it('shows warning banner when neither verified', async () => {
      render(<VerificationBanner />);
      
      await waitFor(() => {
        expect(screen.getByText('Verification Required to Vote')).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /verify email/i })).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /verify phone/i })).toBeInTheDocument();
      });
    });

    it('provides links to verify email and phone', async () => {
      render(<VerificationBanner />);
      
      await waitFor(() => {
        const emailLink = screen.getByRole('link', { name: /verify.*email/i });
        const phoneLink = screen.getByRole('link', { name: /verify.*phone/i });
        
        expect(emailLink).toHaveAttribute('href', expect.stringContaining('verify'));
        expect(phoneLink).toHaveAttribute('href', expect.stringContaining('verify'));
      });
    });
  });

  describe('Error Handling', () => {
    it('renders nothing when fetch fails', async () => {
      mockFetch.mockRejectedValue(new Error('Network error'));
      const { container } = render(<VerificationBanner />);
      
      await waitFor(() => {
        expect(container.firstChild).toBeNull();
      });
    });

    it('renders nothing when response is not ok', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
      });
      const { container } = render(<VerificationBanner />);
      
      await waitFor(() => {
        expect(container.firstChild).toBeNull();
      });
    });
  });

  describe('Custom Styling', () => {
    beforeEach(() => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          email_verified: true,
          phone_verified: true,
        }),
      });
    });

    it('applies custom className', async () => {
      render(<VerificationBanner className="custom-class" />);
      
      await waitFor(() => {
        const badge = screen.getByText('Verified voter').closest('div');
        expect(badge).toHaveClass('custom-class');
      });
    });
  });
});
