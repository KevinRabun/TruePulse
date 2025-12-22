"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

interface VerificationStatus {
  email_verified: boolean;
  phone_verified: boolean;
  both_required: boolean;
}

interface VerificationBannerProps {
  onVerificationComplete?: () => void;
  className?: string;
}

/**
 * Banner showing verification requirements for voting
 * Displays clear CTAs to verify email and/or phone
 */
export function VerificationBanner({
  onVerificationComplete: _onVerificationComplete,
  className = "",
}: VerificationBannerProps) {
  const [status, setStatus] = useState<VerificationStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch("/api/v1/users/me", {
          credentials: "include",
        });
        if (response.ok) {
          const user = await response.json();
          setStatus({
            email_verified: user.email_verified || false,
            phone_verified: user.phone_verified || false,
            both_required: true, // Could be fetched from config endpoint
          });
        }
      } catch (error) {
        console.error("Failed to fetch verification status:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
  }, []);

  if (loading) {
    return null;
  }

  if (!status) {
    return null;
  }

  const { email_verified, phone_verified, both_required } = status;

  // Fully verified - show success badge or nothing
  if (email_verified && phone_verified) {
    return (
      <div className={`flex items-center gap-2 text-green-600 text-sm ${className}`}>
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
            clipRule="evenodd"
          />
        </svg>
        <span>Verified voter</span>
      </div>
    );
  }

  // Not fully verified - show banner
  const missingVerifications = [];
  if (!email_verified) missingVerifications.push("email");
  if (!phone_verified) missingVerifications.push("phone");

  return (
    <div
      className={`rounded-lg border border-amber-200 bg-amber-50 p-4 ${className}`}
    >
      <div className="flex items-start gap-3">
        <div className="shrink-0">
          <svg
            className="h-6 w-6 text-amber-500"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
            />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-amber-800">
            Verification Required to Vote
          </h3>
          <p className="mt-1 text-sm text-amber-700">
            {both_required ? (
              <>
                To ensure fair polls and prevent manipulation, we require{" "}
                <strong>both email and phone verification</strong>. This helps
                ensure one person = one vote.
              </>
            ) : (
              <>
                Please complete verification to participate in polls.
              </>
            )}
          </p>

          <div className="mt-3 flex flex-wrap gap-2">
            {!email_verified && (
              <Link
                href="/settings/verify-email"
                className="inline-flex items-center gap-1.5 rounded-md bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-700 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
                Verify Email
              </Link>
            )}
            {!phone_verified && (
              <Link
                href="/settings/verify-phone"
                className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"
                  />
                </svg>
                Verify Phone
              </Link>
            )}
          </div>

          {/* Progress indicator */}
          <div className="mt-3 flex items-center gap-2">
            <div className="flex items-center gap-1">
              <div
                className={`w-3 h-3 rounded-full ${
                  email_verified ? "bg-green-500" : "bg-gray-300"
                }`}
              />
              <span className="text-xs text-gray-600">Email</span>
            </div>
            <div className="w-4 h-0.5 bg-gray-200" />
            <div className="flex items-center gap-1">
              <div
                className={`w-3 h-3 rounded-full ${
                  phone_verified ? "bg-green-500" : "bg-gray-300"
                }`}
              />
              <span className="text-xs text-gray-600">Phone</span>
            </div>
            <div className="w-4 h-0.5 bg-gray-200" />
            <div className="flex items-center gap-1">
              <div
                className={`w-3 h-3 rounded-full ${
                  email_verified && phone_verified ? "bg-green-500" : "bg-gray-300"
                }`}
              />
              <span className="text-xs text-gray-600">Ready to vote!</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Compact verification badge for headers/navigation
 */
export function VerificationBadge({ className = "" }: { className?: string }) {
  const [verified, setVerified] = useState<boolean | null>(null);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await fetch("/api/v1/users/me", {
          credentials: "include",
        });
        if (response.ok) {
          const user = await response.json();
          setVerified(user.is_verified && user.phone_verified);
        }
      } catch {
        // Ignore errors
      }
    };

    checkStatus();
  }, []);

  if (verified === null) return null;

  return verified ? (
    <span
      className={`inline-flex items-center gap-1 text-xs font-medium text-green-700 bg-green-100 px-2 py-0.5 rounded-full ${className}`}
    >
      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
          clipRule="evenodd"
        />
      </svg>
      Verified
    </span>
  ) : (
    <Link
      href="/settings/verify"
      className={`inline-flex items-center gap-1 text-xs font-medium text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full hover:bg-amber-200 transition-colors ${className}`}
    >
      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
          clipRule="evenodd"
        />
      </svg>
      Verify
    </Link>
  );
}

export default VerificationBanner;
