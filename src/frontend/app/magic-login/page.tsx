'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { useAuthStore } from '@/lib/store';
import {
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';

function MagicLoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  const { setAccessToken, setRefreshToken, setUser } = useAuthStore();

  const [status, setStatus] = useState<'loading' | 'success' | 'error'>(
    token ? 'loading' : 'error'
  );
  const [message, setMessage] = useState(
    token ? '' : 'No login token provided'
  );
  const [needsPasskey, setNeedsPasskey] = useState(false);

  useEffect(() => {
    if (!token) {
      return;
    }

    const verifyMagicLink = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'https://ca-truepulse-api-dev.icyplant-c5249e64.eastus2.azurecontainerapps.io/api/v1'}/auth/verify-magic-link/${token}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (response.ok) {
          const data = await response.json();
          
          // Store tokens
          setAccessToken(data.access_token);
          setRefreshToken(data.refresh_token);
          setUser(data.user);
          
          setStatus('success');
          setMessage('You are now signed in!');
          
          // Check if user needs to set up a passkey
          if (!data.user.has_passkey) {
            setNeedsPasskey(true);
          }
        } else {
          const data = await response.json();
          setStatus('error');
          setMessage(data.detail || 'Failed to sign in. The link may have expired.');
        }
      } catch (_err) {
        setStatus('error');
        setMessage('An error occurred while signing in. Please try again.');
      }
    };

    verifyMagicLink();
  }, [token, setAccessToken, setRefreshToken, setUser]);

  const handleContinue = () => {
    if (needsPasskey) {
      router.push('/setup-passkey');
    } else {
      router.push('/');
    }
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

        {/* Login Card */}
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
                Signing You In
              </h2>
              <p className="text-gray-600 dark:text-slate-400">
                Please wait while we verify your login link...
              </p>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="mx-auto w-16 h-16 bg-linear-to-br from-green-500 to-emerald-500 rounded-full flex items-center justify-center mb-4">
                <CheckCircleIcon className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                Welcome Back!
              </h2>
              <p className="text-gray-600 dark:text-slate-400 mb-6">
                {message}
              </p>
              {needsPasskey && (
                <div className="mb-4 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800/30">
                  <p className="text-sm text-purple-800 dark:text-purple-200">
                    🔐 Set up a passkey for faster, more secure logins in the future.
                  </p>
                </div>
              )}
              <button
                onClick={handleContinue}
                className="w-full py-3 px-4 bg-linear-to-r from-primary-600 to-accent-600 hover:from-primary-700 hover:to-accent-700 text-white font-semibold rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl"
              >
                {needsPasskey ? 'Set Up Passkey' : 'Continue to App'}
              </button>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="mx-auto w-16 h-16 bg-linear-to-br from-red-500 to-rose-500 rounded-full flex items-center justify-center mb-4">
                <XCircleIcon className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                Login Failed
              </h2>
              <p className="text-gray-600 dark:text-slate-400 mb-6">
                {message}
              </p>
              <div className="space-y-3">
                <Link
                  href="/login"
                  className="block w-full py-3 px-4 bg-linear-to-r from-primary-600 to-accent-600 hover:from-primary-700 hover:to-accent-700 text-white font-semibold rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl text-center"
                >
                  Try Again
                </Link>
                <p className="text-sm text-gray-500 dark:text-slate-500">
                  Login links expire after 15 minutes. Request a new one from the login page.
                </p>
              </div>
            </>
          )}
        </motion.div>
      </motion.div>
    </div>
  );
}

function LoadingFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-linear-to-br from-primary-50 via-white to-accent-50 dark:from-slate-900 dark:via-purple-900 dark:to-slate-900 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold bg-linear-to-r from-primary-600 to-accent-600 dark:from-cyan-400 dark:to-purple-400 bg-clip-text text-transparent">
            TruePulse
          </h1>
        </div>
        <div className="bg-white/80 dark:bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-gray-200 dark:border-slate-700/50 p-8 shadow-2xl text-center">
          <div className="mx-auto w-16 h-16 bg-linear-to-br from-primary-500 to-accent-500 rounded-full flex items-center justify-center mb-4">
            <ArrowPathIcon className="w-8 h-8 text-white animate-spin" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Loading...
          </h2>
        </div>
      </div>
    </div>
  );
}

export default function MagicLoginPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <MagicLoginContent />
    </Suspense>
  );
}
