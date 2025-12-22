'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { useAuth } from '@/lib/auth';
import { useToast } from '@/components/ui/toast';
import { isPasskeySupported, hasPlatformAuthenticator } from '@/lib/passkey';
import {
  UserIcon,
  EnvelopeIcon,
  XCircleIcon,
  ShieldCheckIcon,
  FingerPrintIcon,
  DevicePhoneMobileIcon,
} from '@heroicons/react/24/outline';

export default function RegisterPage() {
  const router = useRouter();
  const { register, isLoading } = useAuth();
  const { success, error: showError } = useToast();
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [passkeySupported, setPasskeySupported] = useState<boolean | null>(null);

  useEffect(() => {
    // Check passkey support on mount
    const checkSupport = async () => {
      const supported = isPasskeySupported();
      const hasPlatform = await hasPlatformAuthenticator();
      // User needs both WebAuthn support and platform authenticator for best experience
      setPasskeySupported(supported && hasPlatform);
    };
    checkSupport();
  }, []);

  const isFormValid =
    displayName.length >= 2 &&
    email.includes('@') &&
    acceptTerms &&
    passkeySupported;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!passkeySupported) {
      setError('Your device does not support passkeys. Please use a modern browser.');
      return;
    }

    if (!isFormValid) {
      setError('Please fill in all fields correctly.');
      return;
    }

    try {
      await register({ 
        email, 
        username: email.split('@')[0],
        display_name: displayName 
      });
      success('Account created!', 'Now let\'s set up your passkey for secure login.');
      // Redirect to passkey setup
      router.push('/setup-passkey');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Registration failed. Please try again.';
      setError(errorMessage);
      showError('Registration failed', errorMessage);
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
          <p className="mt-2 text-gray-600 dark:text-slate-400">Create your account and start participating</p>
        </div>

        {/* Register Card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className="bg-white/80 dark:bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-gray-200 dark:border-slate-700/50 p-8 shadow-2xl"
        >
          {/* Passkey Security Badge */}
          <div className="mb-6 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
            <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
              <ShieldCheckIcon className="h-5 w-5" />
              <span className="text-sm font-medium">Passwordless Security</span>
            </div>
            <p className="mt-1 text-xs text-green-600 dark:text-green-500">
              TruePulse uses passkeys instead of passwords - more secure and easier to use
            </p>
          </div>

          {/* Passkey Not Supported Warning */}
          {passkeySupported === false && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 bg-yellow-100 dark:bg-yellow-900/20 border border-yellow-300 dark:border-yellow-700 rounded-lg p-4"
            >
              <div className="flex items-center gap-2 text-yellow-700 dark:text-yellow-400 mb-2">
                <XCircleIcon className="h-5 w-5" />
                <span className="font-medium">Passkeys Not Supported</span>
              </div>
              <p className="text-sm text-yellow-600 dark:text-yellow-500">
                Your browser or device doesn&apos;t support passkeys. Please use a modern browser like Chrome, Safari, or Edge to register.
              </p>
              <a
                href="https://passkeys.dev/device-support/"
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-block text-sm text-yellow-700 dark:text-yellow-400 hover:underline"
              >
                Check device compatibility →
              </a>
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Error Message */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-red-100 dark:bg-red-500/10 border border-red-300 dark:border-red-500/50 rounded-lg p-4 text-red-700 dark:text-red-400 text-sm"
              >
                {error}
              </motion.div>
            )}

            {/* Display Name Field */}
            <div>
              <label htmlFor="displayName" className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
                Display Name
              </label>
              <div className="relative">
                <UserIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 dark:text-slate-500" />
                <input
                  id="displayName"
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  required
                  minLength={2}
                  maxLength={50}
                  className="w-full pl-10 pr-4 py-3 bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-slate-500 focus:outline-hidden focus:ring-2 focus:ring-primary-500 dark:focus:ring-purple-500 focus:border-transparent transition-all"
                  placeholder="Your display name"
                />
              </div>
              <p className="mt-1 text-xs text-gray-500 dark:text-slate-500">This will be shown on leaderboards</p>
            </div>

            {/* Email Field */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
                Email
              </label>
              <div className="relative">
                <EnvelopeIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 dark:text-slate-500" />
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  className="w-full pl-10 pr-4 py-3 bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-slate-500 focus:outline-hidden focus:ring-2 focus:ring-primary-500 dark:focus:ring-purple-500 focus:border-transparent transition-all"
                  placeholder="you@example.com"
                />
              </div>
            </div>

            {/* Terms Checkbox */}
            <div className="flex items-start gap-3">
              <input
                id="terms"
                type="checkbox"
                checked={acceptTerms}
                onChange={(e) => setAcceptTerms(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-gray-300 dark:border-slate-700 bg-gray-50 dark:bg-slate-900/50 text-primary-600 dark:text-purple-600 focus:ring-primary-500 dark:focus:ring-purple-500 focus:ring-offset-white dark:focus:ring-offset-slate-900"
              />
              <label htmlFor="terms" className="text-sm text-gray-600 dark:text-slate-400">
                I agree to the{' '}
                <Link href="/terms" className="text-primary-600 dark:text-purple-400 hover:text-primary-500 dark:hover:text-purple-300">
                  Terms of Service
                </Link>{' '}
                and{' '}
                <Link href="/privacy" className="text-primary-600 dark:text-purple-400 hover:text-primary-500 dark:hover:text-purple-300">
                  Privacy Policy
                </Link>
              </label>
            </div>

            {/* What happens next */}
            <div className="p-4 bg-gray-50 dark:bg-slate-900/30 rounded-lg">
              <p className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">What happens next:</p>
              <ol className="text-xs text-gray-600 dark:text-slate-400 space-y-1.5">
                <li className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-primary-100 dark:bg-purple-900/50 text-primary-600 dark:text-purple-400 flex items-center justify-center text-[10px] font-bold">1</span>
                  Verify your email address
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-primary-100 dark:bg-purple-900/50 text-primary-600 dark:text-purple-400 flex items-center justify-center text-[10px] font-bold">2</span>
                  Create your passkey (Face ID, Touch ID, or PIN)
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-primary-100 dark:bg-purple-900/50 text-primary-600 dark:text-purple-400 flex items-center justify-center text-[10px] font-bold">3</span>
                  Start voting on daily polls!
                </li>
              </ol>
            </div>

            {/* Submit Button */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              type="submit"
              disabled={isLoading || !isFormValid}
              className="w-full py-3 px-4 bg-linear-to-r from-primary-600 to-accent-600 dark:from-purple-600 dark:to-cyan-600 text-white font-semibold rounded-lg hover:from-primary-500 hover:to-accent-500 dark:hover:from-purple-500 dark:hover:to-cyan-500 focus:outline-hidden focus:ring-2 focus:ring-primary-500 dark:focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {isLoading ? (
                <div className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Creating account...
                </div>
              ) : (
                'Continue'
              )}
            </motion.button>
          </form>

          {/* Login Link */}
          <p className="mt-6 text-center text-gray-600 dark:text-slate-400">
            Already have an account?{' '}
            <Link href="/login" className="text-primary-600 dark:text-purple-400 hover:text-primary-500 dark:hover:text-purple-300 font-medium transition-colors">
              Sign in
            </Link>
          </p>
        </motion.div>

        {/* Security Features */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-6"
        >
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="p-3 bg-white/50 dark:bg-slate-800/30 rounded-lg">
              <FingerPrintIcon className="h-6 w-6 mx-auto text-purple-500 mb-1" />
              <p className="text-xs text-gray-600 dark:text-slate-400">Biometric Login</p>
            </div>
            <div className="p-3 bg-white/50 dark:bg-slate-800/30 rounded-lg">
              <ShieldCheckIcon className="h-6 w-6 mx-auto text-green-500 mb-1" />
              <p className="text-xs text-gray-600 dark:text-slate-400">Phishing-proof</p>
            </div>
            <div className="p-3 bg-white/50 dark:bg-slate-800/30 rounded-lg">
              <DevicePhoneMobileIcon className="h-6 w-6 mx-auto text-blue-500 mb-1" />
              <p className="text-xs text-gray-600 dark:text-slate-400">Device-bound</p>
            </div>
          </div>
          <p className="mt-4 text-center text-sm text-gray-500 dark:text-slate-500">
            🔒 Your votes are anonymous and cannot be traced back to you
          </p>
        </motion.div>
      </motion.div>
    </div>
  );
}
