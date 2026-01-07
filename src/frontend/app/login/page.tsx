'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { useAuth } from '@/lib/auth';
import { useToast } from '@/components/ui/toast';
import { PasskeyLoginButton } from '@/components/auth';
import { isPasskeySupported, hasPlatformAuthenticator } from '@/lib/passkey';
import { api } from '@/lib/api';
import { FingerPrintIcon, ShieldCheckIcon, DevicePhoneMobileIcon, EnvelopeIcon } from '@heroicons/react/24/outline';

export default function LoginPage() {
  const router = useRouter();
  const { isAuthenticated, refreshUser } = useAuth();
  const { success, error: showError } = useToast();
  const [error, setError] = useState<string | null>(null);
  // Initialize passkey support synchronously to avoid setState in effect
  const [passkeySupported] = useState<boolean | null>(() => 
    typeof window !== 'undefined' ? isPasskeySupported() : null
  );
  const [, setHasPlatform] = useState<boolean | null>(null);
  const [showMagicLink, setShowMagicLink] = useState(false);
  const [magicLinkEmail, setMagicLinkEmail] = useState('');
  const [magicLinkSent, setMagicLinkSent] = useState(false);
  const [magicLinkLoading, setMagicLinkLoading] = useState(false);
  const [showNotFound, setShowNotFound] = useState(false);

  useEffect(() => {
    // Only check async platform authenticator in effect
    hasPlatformAuthenticator().then(setHasPlatform);
    
    // Redirect if already authenticated
    if (isAuthenticated) {
      router.push('/');
    }
  }, [isAuthenticated, router]);

  const handlePasskeySuccess = async () => {
    success('Welcome back!', 'You are now signed in with your passkey.');
    await refreshUser();
    router.push('/');
  };

  const handlePasskeyError = (errorMsg: string) => {
    setError(errorMsg);
    showError('Login failed', errorMsg);
  };

  const handleSendMagicLink = async (e: React.FormEvent) => {
    e.preventDefault();
    setMagicLinkLoading(true);
    setError(null);
    setShowNotFound(false);
    
    try {
      const response = await api.sendMagicLink(magicLinkEmail);
      if (response.status === 'not_found') {
        setShowNotFound(true);
      } else {
        setMagicLinkSent(true);
        success('Check your email', 'We sent you a login link. Click it to sign in.');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to send login link';
      setError(message);
      showError('Failed to send link', message);
    } finally {
      setMagicLinkLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-linear-to-br from-primary-50 via-white to-accent-50 dark:from-slate-900 dark:via-purple-900 dark:to-slate-900 px-4">
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
          <p className="mt-2 text-gray-600 dark:text-slate-400">Sign in to participate in daily polls</p>
        </div>

        {/* Login Card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className="bg-white/80 dark:bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-gray-200 dark:border-slate-700/50 p-8 shadow-2xl"
        >
          {/* Error Message */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 bg-red-100 dark:bg-red-500/10 border border-red-300 dark:border-red-500/50 rounded-lg p-4 text-red-700 dark:text-red-400 text-sm"
            >
              {error}
            </motion.div>
          )}

          {/* Passkey Login */}
          {passkeySupported && !showMagicLink ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-6"
            >
              {/* Security Badge */}
              <div className="flex items-center justify-center gap-2 text-sm text-gray-600 dark:text-slate-400">
                <ShieldCheckIcon className="h-5 w-5 text-green-500" />
                <span>Passwordless authentication</span>
              </div>
              
              <PasskeyLoginButton
                onSuccess={handlePasskeySuccess}
                onError={handlePasskeyError}
                className="w-full"
              />

              {/* Benefits */}
              <div className="pt-4 border-t border-gray-200 dark:border-slate-700">
                <p className="text-xs text-center text-gray-500 dark:text-slate-500 mb-3">
                  Why passkeys?
                </p>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="p-2">
                    <FingerPrintIcon className="h-6 w-6 mx-auto text-purple-500 mb-1" />
                    <p className="text-xs text-gray-600 dark:text-slate-400">Biometric</p>
                  </div>
                  <div className="p-2">
                    <ShieldCheckIcon className="h-6 w-6 mx-auto text-green-500 mb-1" />
                    <p className="text-xs text-gray-600 dark:text-slate-400">Phishing-proof</p>
                  </div>
                  <div className="p-2">
                    <DevicePhoneMobileIcon className="h-6 w-6 mx-auto text-blue-500 mb-1" />
                    <p className="text-xs text-gray-600 dark:text-slate-400">Device-bound</p>
                  </div>
                </div>
              </div>

              {/* Magic Link Alternative */}
              <div className="pt-4 border-t border-gray-200 dark:border-slate-700">
                <button
                  onClick={() => setShowMagicLink(true)}
                  className="w-full text-sm text-gray-500 dark:text-slate-400 hover:text-primary-600 dark:hover:text-purple-400 transition-colors cursor-pointer"
                >
                  <EnvelopeIcon className="h-4 w-4 inline-block mr-1" />
                  No passkey? Sign in with email link
                </button>
              </div>
            </motion.div>
          ) : showMagicLink ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-6"
            >
              {showNotFound ? (
                <div className="text-center py-4">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                    <EnvelopeIcon className="h-8 w-8 text-amber-600 dark:text-amber-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                    No account found
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-slate-400 mb-4">
                    We couldn&apos;t find an account for <strong>{magicLinkEmail}</strong>.
                  </p>
                  <p className="text-sm text-gray-600 dark:text-slate-400 mb-6">
                    Would you like to create a new account?
                  </p>
                  <Link
                    href={`/register?email=${encodeURIComponent(magicLinkEmail)}`}
                    className="inline-block w-full py-3 px-4 rounded-lg bg-primary-600 dark:bg-purple-600 text-white font-medium hover:bg-primary-700 dark:hover:bg-purple-700 transition-colors text-center"
                  >
                    Create an account
                  </Link>
                  <button
                    onClick={() => {
                      setShowNotFound(false);
                      setMagicLinkEmail('');
                    }}
                    className="mt-4 text-sm text-gray-500 dark:text-slate-400 hover:text-primary-600 dark:hover:text-purple-400 transition-colors cursor-pointer w-full"
                  >
                    Try a different email
                  </button>
                </div>
              ) : magicLinkSent ? (
                <div className="text-center py-4">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                    <EnvelopeIcon className="h-8 w-8 text-green-600 dark:text-green-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                    Check your email
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-slate-400 mb-4">
                    We sent a login link to <strong>{magicLinkEmail}</strong>. Click it to sign in.
                  </p>
                  <p className="text-xs text-gray-500 dark:text-slate-500">
                    The link expires in 15 minutes.
                  </p>
                  <button
                    onClick={() => {
                      setMagicLinkSent(false);
                      setMagicLinkEmail('');
                    }}
                    className="mt-4 text-sm text-primary-600 dark:text-purple-400 hover:underline cursor-pointer"
                  >
                    Send to a different email
                  </button>
                </div>
              ) : (
                <>
                  <div className="text-center">
                    <EnvelopeIcon className="h-12 w-12 mx-auto text-primary-600 dark:text-purple-400 mb-2" />
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
                      Sign in with email
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-slate-400">
                      We&apos;ll send you a link to sign in
                    </p>
                  </div>
                  
                  <form onSubmit={handleSendMagicLink} className="space-y-4">
                    <div>
                      <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                        Email address
                      </label>
                      <input
                        type="email"
                        id="email"
                        value={magicLinkEmail}
                        onChange={(e) => setMagicLinkEmail(e.target.value)}
                        required
                        className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 dark:focus:ring-purple-500 focus:border-transparent transition-colors"
                        placeholder="you@example.com"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={magicLinkLoading}
                      className="w-full py-3 px-4 rounded-lg bg-primary-600 dark:bg-purple-600 text-white font-medium hover:bg-primary-700 dark:hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {magicLinkLoading ? 'Sending...' : 'Send login link'}
                    </button>
                  </form>
                </>
              )}

              {passkeySupported && (
                <div className="pt-4 border-t border-gray-200 dark:border-slate-700">
                  <button
                    onClick={() => {
                      setShowMagicLink(false);
                      setMagicLinkSent(false);
                      setMagicLinkEmail('');
                    }}
                    className="w-full text-sm text-gray-500 dark:text-slate-400 hover:text-primary-600 dark:hover:text-purple-400 transition-colors cursor-pointer"
                  >
                    <FingerPrintIcon className="h-4 w-4 inline-block mr-1" />
                    Sign in with passkey instead
                  </button>
                </div>
              )}
            </motion.div>
          ) : (
            <div className="text-center py-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-yellow-100 dark:bg-yellow-900/30 flex items-center justify-center">
                <ShieldCheckIcon className="h-8 w-8 text-yellow-600 dark:text-yellow-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Passkeys Not Supported
              </h3>
              <p className="text-sm text-gray-600 dark:text-slate-400 mb-4">
                Your browser or device doesn&apos;t support passkeys. You can sign in with an email link instead.
              </p>
              <button
                onClick={() => setShowMagicLink(true)}
                className="inline-flex items-center gap-2 py-2 px-4 rounded-lg bg-primary-600 dark:bg-purple-600 text-white font-medium hover:bg-primary-700 dark:hover:bg-purple-700 transition-colors"
              >
                <EnvelopeIcon className="h-5 w-5" />
                Sign in with email link
              </button>
            </div>
          )}

          {/* Register Link */}
          <p className="mt-6 text-center text-gray-600 dark:text-slate-400">
            Don&apos;t have an account?{' '}
            <Link href="/register" className="text-primary-600 dark:text-purple-400 hover:text-primary-500 dark:hover:text-purple-300 font-medium transition-colors">
              Sign up
            </Link>
          </p>
        </motion.div>

        {/* Security Notice */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-6 text-center"
        >
          <p className="text-sm text-gray-500 dark:text-slate-500">
            🔒 Your votes are anonymous and cannot be traced back to you
          </p>
          <p className="mt-2 text-xs text-gray-400 dark:text-slate-600">
            TruePulse uses passkey authentication - no passwords to remember or steal
          </p>
        </motion.div>
      </motion.div>
    </div>
  );
}
