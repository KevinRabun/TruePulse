'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { useAuth } from '@/lib/auth';
import { useToast } from '@/components/ui/toast';
import { PasskeyLoginButton } from '@/components/auth';
import { isPasskeySupported, hasPlatformAuthenticator } from '@/lib/passkey';
import { FingerPrintIcon, ShieldCheckIcon, DevicePhoneMobileIcon } from '@heroicons/react/24/outline';

export default function LoginPage() {
  const router = useRouter();
  const { isAuthenticated, refreshUser } = useAuth();
  const { success, error: showError } = useToast();
  const [error, setError] = useState<string | null>(null);
  const [passkeySupported, setPasskeySupported] = useState<boolean | null>(null);
  const [, setHasPlatform] = useState<boolean | null>(null);

  useEffect(() => {
    // Check passkey support
    setPasskeySupported(isPasskeySupported());
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

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-accent-50 dark:from-slate-900 dark:via-purple-900 dark:to-slate-900 px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-block">
            <h1 className="text-4xl font-bold bg-gradient-to-r from-primary-600 to-accent-600 dark:from-cyan-400 dark:to-purple-400 bg-clip-text text-transparent">
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
          {passkeySupported ? (
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
                Your browser or device doesn&apos;t support passkeys. Please use a modern browser like Chrome, Safari, or Edge.
              </p>
              <a
                href="https://passkeys.dev/device-support/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-primary-600 dark:text-purple-400 hover:underline"
              >
                Check device compatibility →
              </a>
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
