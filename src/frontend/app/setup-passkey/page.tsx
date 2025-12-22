'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { useAuthStore } from '@/lib/store';
import { useToast } from '@/components/ui/toast';
import { PasskeyRegister } from '@/components/auth';
import {
  ShieldCheckIcon,
  FingerPrintIcon,
  CheckCircleIcon,
  ArrowRightIcon,
} from '@heroicons/react/24/outline';

export default function SetupPasskeyPage() {
  const router = useRouter();
  const { accessToken } = useAuthStore();
  const { success, error: showError } = useToast();
  const [passkeyCreated, setPasskeyCreated] = useState(false);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!accessToken) {
      router.push('/login');
    }
  }, [accessToken, router]);

  const handlePasskeySuccess = (_passkey: { id: string; deviceName: string }) => {
    setPasskeyCreated(true);
    success('Passkey created!', 'Your account is now secured with passkey authentication.');
  };

  const handlePasskeyError = (errorMsg: string) => {
    showError('Passkey setup failed', errorMsg);
  };

  const handleContinue = () => {
    router.push('/');
  };

  const handleSkip = () => {
    // Allow skip but show warning
    router.push('/');
  };

  if (!accessToken) {
    return null; // Will redirect
  }

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
          <p className="mt-2 text-gray-600 dark:text-slate-400">
            {passkeyCreated ? 'You\'re all set!' : 'One more step to secure your account'}
          </p>
        </div>

        {/* Setup Card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className="bg-white/80 dark:bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-gray-200 dark:border-slate-700/50 p-8 shadow-2xl"
        >
          {!passkeyCreated ? (
            <>
              {/* Header */}
              <div className="text-center mb-6">
                <div className="mx-auto w-16 h-16 bg-linear-to-br from-primary-500 to-accent-500 rounded-full flex items-center justify-center mb-4">
                  <FingerPrintIcon className="w-8 h-8 text-white" />
                </div>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Set Up Your Passkey
                </h2>
                <p className="mt-2 text-gray-600 dark:text-slate-400">
                  Passkeys are more secure than passwords and easier to use
                </p>
              </div>

              {/* Security Info */}
              <div className="mb-6 p-4 bg-primary-50 dark:bg-primary-900/20 rounded-lg border border-primary-100 dark:border-primary-800/30">
                <div className="flex items-start gap-3">
                  <ShieldCheckIcon className="w-5 h-5 text-primary-600 dark:text-primary-400 mt-0.5 shrink-0" />
                  <div className="text-sm">
                    <p className="text-primary-900 dark:text-primary-100 font-medium">
                      Why passkeys?
                    </p>
                    <ul className="mt-1 text-primary-700 dark:text-primary-300 space-y-1">
                      <li>• Can&apos;t be phished or stolen</li>
                      <li>• Works with Face ID, Touch ID, or PIN</li>
                      <li>• Syncs across your devices</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Passkey Register Component */}
              <PasskeyRegister
                onSuccess={handlePasskeySuccess}
                onError={handlePasskeyError}
                className="mb-6"
              />

              {/* Skip Option */}
              <div className="text-center">
                <button
                  onClick={handleSkip}
                  className="text-sm text-gray-500 dark:text-slate-500 hover:text-gray-700 dark:hover:text-slate-300 transition-colors"
                >
                  Skip for now (not recommended)
                </button>
              </div>
            </>
          ) : (
            /* Success State */
            <div className="text-center">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', duration: 0.5 }}
                className="mx-auto w-20 h-20 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mb-6"
              >
                <CheckCircleIcon className="w-12 h-12 text-green-600 dark:text-green-400" />
              </motion.div>
              
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                Passkey Created!
              </h2>
              <p className="text-gray-600 dark:text-slate-400 mb-6">
                Your account is now protected with passkey authentication. You can sign in securely using Face ID, Touch ID, or your device PIN.
              </p>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleContinue}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-linear-to-r from-primary-600 to-accent-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all"
              >
                Start Exploring
                <ArrowRightIcon className="w-5 h-5" />
              </motion.button>
            </div>
          )}
        </motion.div>

        {/* Help Text */}
        <p className="text-center text-sm text-gray-500 dark:text-slate-500 mt-6">
          Having trouble?{' '}
          <Link href="/security" className="text-primary-600 dark:text-primary-400 hover:underline">
            Learn more about passkeys
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
