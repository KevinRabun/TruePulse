'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  ShieldCheckIcon,
  EnvelopeIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';
import { CheckCircleIcon as CheckCircleSolidIcon } from '@heroicons/react/24/solid';

interface VerificationStatusProps {
  emailVerified: boolean;
  email?: string;
  onResendEmail?: () => void;
}

/**
 * Verification Status component for the Settings page.
 * Shows the current verification status for email,
 * and provides CTAs to complete verification if needed.
 */
export function VerificationStatus({
  emailVerified,
  email,
  onResendEmail,
}: VerificationStatusProps) {
  const [resendingEmail, setResendingEmail] = useState(false);

  const handleResendEmail = async () => {
    if (!onResendEmail) return;
    setResendingEmail(true);
    try {
      await onResendEmail();
    } finally {
      setResendingEmail(false);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-gray-200 dark:border-slate-700/50 p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className={`p-2 rounded-lg ${emailVerified ? 'bg-green-100 dark:bg-green-500/20' : 'bg-amber-100 dark:bg-amber-500/20'}`}>
          <ShieldCheckIcon className={`h-6 w-6 ${emailVerified ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400'}`} />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Verification Status</h3>
          <p className="text-sm text-gray-600 dark:text-slate-400">
            {emailVerified
              ? 'Your email is verified'
              : 'Verify your email to complete account setup'}
          </p>
        </div>
        {emailVerified && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="ml-auto"
          >
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-green-100 dark:bg-green-500/20 text-green-700 dark:text-green-400 text-sm font-medium">
              <CheckCircleSolidIcon className="h-4 w-4" />
              Verified
            </span>
          </motion.div>
        )}
      </div>

      {/* Email Verification Status */}
      <div className={`p-4 rounded-lg border ${
        emailVerified
          ? 'bg-green-50 dark:bg-green-500/10 border-green-200 dark:border-green-500/30'
          : 'bg-gray-50 dark:bg-slate-900/30 border-gray-200 dark:border-slate-700/50'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-full ${
              emailVerified
                ? 'bg-green-100 dark:bg-green-500/20'
                : 'bg-gray-200 dark:bg-slate-700/50'
            }`}>
              {emailVerified ? (
                <CheckCircleIcon className="h-5 w-5 text-green-600 dark:text-green-400" />
              ) : (
                <EnvelopeIcon className="h-5 w-5 text-gray-500 dark:text-slate-400" />
              )}
            </div>
            <div>
              <p className={`font-medium ${
                emailVerified ? 'text-green-700 dark:text-green-400' : 'text-gray-900 dark:text-white'
              }`}>
                Email Verification
              </p>
              <p className="text-sm text-gray-600 dark:text-slate-400">
                {emailVerified
                  ? `Verified: ${email || 'your email'}`
                  : 'Check your inbox for a verification link'}
              </p>
            </div>
          </div>
          {!emailVerified && (
            <button
              onClick={handleResendEmail}
              disabled={resendingEmail || !onResendEmail}
              className="px-3 py-1.5 text-sm font-medium text-primary-600 dark:text-cyan-400 hover:text-primary-700 dark:hover:text-cyan-300 hover:bg-primary-50 dark:hover:bg-cyan-500/10 rounded-lg transition-colors disabled:opacity-50"
            >
              {resendingEmail ? 'Sending...' : 'Resend Email'}
            </button>
          )}
        </div>
      </div>

      {/* Info Banner for unverified */}
      {!emailVerified && (
        <div className="mt-6 p-4 rounded-lg bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/30">
          <div className="flex items-start gap-3">
            <ExclamationCircleIcon className="h-5 w-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
                Why do I need to verify my email?
              </p>
              <p className="text-sm text-amber-700 dark:text-amber-400/80 mt-1">
                Email verification helps secure your account and ensures you can recover access if needed.
                Combined with your passkey, this provides strong account security.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Success Message */}
      {emailVerified && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-6 p-4 rounded-lg bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/30"
        >
          <div className="flex items-start gap-3">
            <CheckCircleSolidIcon className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-green-800 dark:text-green-300">
                You&apos;re ready to vote!
              </p>
              <p className="text-sm text-green-700 dark:text-green-400/80 mt-1">
                Your account is verified. You can now participate in all polls and have your voice heard.
              </p>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
