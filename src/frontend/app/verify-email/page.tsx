'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';

export default function VerifyEmailPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token');

  const [status, setStatus] = useState<'loading' | 'success' | 'error'>(
    token ? 'loading' : 'error'
  );
  const [message, setMessage] = useState(
    token ? '' : 'No verification token provided'
  );

  useEffect(() => {
    if (!token) {
      return;
    }

    const verifyEmail = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'https://ca-truepulse-api-dev.icyplant-c5249e64.eastus2.azurecontainerapps.io'}/api/v1/auth/verify-email/${token}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (response.ok) {
          setStatus('success');
          setMessage('Your email has been verified successfully!');
        } else {
          const data = await response.json();
          setStatus('error');
          setMessage(data.detail || 'Failed to verify email. The link may have expired.');
        }
      } catch (_err) {
        setStatus('error');
        setMessage('An error occurred while verifying your email. Please try again.');
      }
    };

    verifyEmail();
  }, [token]);

  const handleContinue = () => {
    router.push('/login');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-linear-to-br from-primary-50 via-white to-accent-50 dark:from-slate-900 dark:via-purple-900 dark:to-slate-900 px-4 py-12">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-block">
            <h1 className="text-4xl font-bold bg-linear-to-r from-primary-600 to-accent-600 dark:from-cyan-400 dark:to-purple-400 bg-clip-text text-transparent">
              TruePulse
            </h1>
          </Link>
        </div>

        {/* Verification Card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className="bg-white/80 dark:bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-gray-200 dark:border-slate-700/50 p-8 shadow-2xl text-center"
        >
          {status === 'loading' && (
            <>
              <div className="mx-auto w-16 h-16 bg-linear-to-br from-primary-500 to-accent-500 rounded-full flex items-center justify-center mb-4">
                <ArrowPathIcon className="w-8 h-8 text-white animate-spin" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                Verifying Your Email
              </h2>
              <p className="text-gray-600 dark:text-slate-400">
                Please wait while we verify your email address...
              </p>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="mx-auto w-16 h-16 bg-linear-to-br from-green-500 to-emerald-500 rounded-full flex items-center justify-center mb-4">
                <CheckCircleIcon className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                Email Verified!
              </h2>
              <p className="text-gray-600 dark:text-slate-400 mb-6">
                {message}
              </p>
              <button
                onClick={handleContinue}
                className="w-full py-3 px-4 bg-linear-to-r from-primary-600 to-accent-600 hover:from-primary-700 hover:to-accent-700 text-white font-semibold rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl"
              >
                Continue to Login
              </button>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="mx-auto w-16 h-16 bg-linear-to-br from-red-500 to-rose-500 rounded-full flex items-center justify-center mb-4">
                <XCircleIcon className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                Verification Failed
              </h2>
              <p className="text-gray-600 dark:text-slate-400 mb-6">
                {message}
              </p>
              <div className="space-y-3">
                <Link
                  href="/login"
                  className="block w-full py-3 px-4 bg-linear-to-r from-primary-600 to-accent-600 hover:from-primary-700 hover:to-accent-700 text-white font-semibold rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl text-center"
                >
                  Go to Login
                </Link>
                <p className="text-sm text-gray-500 dark:text-slate-500">
                  Need a new verification link? Log in and request a new one from your profile.
                </p>
              </div>
            </>
          )}
        </motion.div>
      </motion.div>
    </div>
  );
}
