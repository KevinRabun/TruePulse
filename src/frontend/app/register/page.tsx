'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { useAuth } from '@/lib/auth';
import { useToast } from '@/components/ui/toast';
import {
  UserIcon,
  EnvelopeIcon,
  LockClosedIcon,
  EyeIcon,
  EyeSlashIcon,
  CheckCircleIcon,
  XCircleIcon,
  PhoneIcon,
  ChatBubbleLeftIcon,
} from '@heroicons/react/24/outline';

const passwordRequirements = [
  { id: 'length', label: 'At least 8 characters', test: (p: string) => p.length >= 8 },
  { id: 'uppercase', label: 'One uppercase letter', test: (p: string) => /[A-Z]/.test(p) },
  { id: 'lowercase', label: 'One lowercase letter', test: (p: string) => /[a-z]/.test(p) },
  { id: 'number', label: 'One number', test: (p: string) => /\d/.test(p) },
];

export default function RegisterPage() {
  const router = useRouter();
  const { register, isLoading } = useAuth();
  const { success, error: showError } = useToast();
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [acceptSms, setAcceptSms] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Validate phone number format (US format or international)
  const isValidPhone = (phone: string) => {
    const cleaned = phone.replace(/[\s\-\(\)\.]/g, '');
    return /^\+?[0-9]{10,15}$/.test(cleaned);
  };

  const passwordStrength = passwordRequirements.filter((req) => req.test(password)).length;
  const passwordsMatch = password === confirmPassword && password.length > 0;
  const phoneValid = isValidPhone(phoneNumber);
  const isFormValid =
    displayName.length >= 2 &&
    email.includes('@') &&
    phoneValid &&
    passwordStrength === passwordRequirements.length &&
    passwordsMatch &&
    acceptTerms &&
    acceptSms;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!isFormValid) {
      setError('Please fill in all fields correctly.');
      return;
    }

    try {
      // Clean phone number before sending
      const cleanedPhone = phoneNumber.replace(/[\s\-\(\)\.]/g, '');
      await register({ 
        email, 
        password, 
        username: email.split('@')[0], 
        phone_number: cleanedPhone,
        display_name: displayName 
      });
      success('Account created!', 'Welcome to TruePulse. Please verify your phone number to start voting.');
      router.push('/');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Registration failed. Please try again.';
      setError(errorMessage);
      showError('Registration failed', errorMessage);
    }
  };

  const getStrengthColor = () => {
    if (passwordStrength <= 1) return 'bg-red-500';
    if (passwordStrength <= 2) return 'bg-orange-500';
    if (passwordStrength <= 3) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-accent-50 dark:from-slate-900 dark:via-purple-900 dark:to-slate-900 px-4 py-12">
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
          <p className="mt-2 text-gray-600 dark:text-slate-400">Create your account and start participating</p>
        </div>

        {/* Register Card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className="bg-white/80 dark:bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-gray-200 dark:border-slate-700/50 p-8 shadow-2xl"
        >
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
                  className="w-full pl-10 pr-4 py-3 bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:focus:ring-purple-500 focus:border-transparent transition-all"
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
                  className="w-full pl-10 pr-4 py-3 bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:focus:ring-purple-500 focus:border-transparent transition-all"
                  placeholder="you@example.com"
                />
              </div>
            </div>

            {/* Phone Number Field */}
            <div>
              <label htmlFor="phoneNumber" className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
                Phone Number <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <PhoneIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 dark:text-slate-500" />
                <input
                  id="phoneNumber"
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  required
                  autoComplete="tel"
                  className={`w-full pl-10 pr-4 py-3 bg-gray-50 dark:bg-slate-900/50 border rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:focus:ring-purple-500 focus:border-transparent transition-all ${
                    phoneNumber.length > 0
                      ? phoneValid
                        ? 'border-green-500'
                        : 'border-red-500'
                      : 'border-gray-300 dark:border-slate-700'
                  }`}
                  placeholder="+1 (555) 123-4567"
                />
                {phoneNumber.length > 0 && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    {phoneValid ? (
                      <CheckCircleIcon className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircleIcon className="h-5 w-5 text-red-500" />
                    )}
                  </div>
                )}
              </div>
              <p className="mt-1 text-xs text-gray-500 dark:text-slate-500">
                Required for account verification. We use SMS to verify you&apos;re a real person.
              </p>
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
                Password
              </label>
              <div className="relative">
                <LockClosedIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 dark:text-slate-500" />
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="new-password"
                  className="w-full pl-10 pr-12 py-3 bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:focus:ring-purple-500 focus:border-transparent transition-all"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-400 transition-colors"
                >
                  {showPassword ? <EyeSlashIcon className="h-5 w-5" /> : <EyeIcon className="h-5 w-5" />}
                </button>
              </div>

              {/* Password Strength */}
              {password.length > 0 && (
                <div className="mt-3 space-y-2">
                  <div className="flex gap-1">
                    {[...Array(4)].map((_, i) => (
                      <div
                        key={i}
                        className={`h-1 flex-1 rounded-full transition-colors ${
                          i < passwordStrength ? getStrengthColor() : 'bg-gray-200 dark:bg-slate-700'
                        }`}
                      />
                    ))}
                  </div>
                  <div className="grid grid-cols-2 gap-1">
                    {passwordRequirements.map((req) => (
                      <div key={req.id} className="flex items-center gap-1 text-xs">
                        {req.test(password) ? (
                          <CheckCircleIcon className="h-3.5 w-3.5 text-green-500" />
                        ) : (
                          <XCircleIcon className="h-3.5 w-3.5 text-gray-400 dark:text-slate-600" />
                        )}
                        <span className={req.test(password) ? 'text-green-500' : 'text-gray-500 dark:text-slate-500'}>
                          {req.label}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Confirm Password Field */}
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
                Confirm Password
              </label>
              <div className="relative">
                <LockClosedIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 dark:text-slate-500" />
                <input
                  id="confirmPassword"
                  type={showPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  autoComplete="new-password"
                  className={`w-full pl-10 pr-12 py-3 bg-gray-50 dark:bg-slate-900/50 border rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:focus:ring-purple-500 focus:border-transparent transition-all ${
                    confirmPassword.length > 0
                      ? passwordsMatch
                        ? 'border-green-500'
                        : 'border-red-500'
                      : 'border-gray-300 dark:border-slate-700'
                  }`}
                  placeholder="••••••••"
                />
                {confirmPassword.length > 0 && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    {passwordsMatch ? (
                      <CheckCircleIcon className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircleIcon className="h-5 w-5 text-red-500" />
                    )}
                  </div>
                )}
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

            {/* SMS Consent Checkbox */}
            <div className="flex items-start gap-3 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <input
                id="smsConsent"
                type="checkbox"
                checked={acceptSms}
                onChange={(e) => setAcceptSms(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-gray-300 dark:border-slate-700 bg-gray-50 dark:bg-slate-900/50 text-primary-600 dark:text-purple-600 focus:ring-primary-500 dark:focus:ring-purple-500 focus:ring-offset-white dark:focus:ring-offset-slate-900"
              />
              <label htmlFor="smsConsent" className="text-sm text-gray-700 dark:text-slate-300">
                <span className="flex items-center gap-1.5 font-medium mb-1">
                  <ChatBubbleLeftIcon className="h-4 w-4 text-blue-500" />
                  SMS Verification Consent <span className="text-red-500">*</span>
                </span>
                <span className="text-gray-600 dark:text-slate-400">
                  I consent to receive SMS messages from TruePulse for account verification purposes. 
                  Phone verification is required to ensure one person = one vote and prevent fraud. 
                  Standard message and data rates may apply.
                </span>
              </label>
            </div>

            {/* Submit Button */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              type="submit"
              disabled={isLoading || !isFormValid}
              className="w-full py-3 px-4 bg-gradient-to-r from-primary-600 to-accent-600 dark:from-purple-600 dark:to-cyan-600 text-white font-semibold rounded-lg hover:from-primary-500 hover:to-accent-500 dark:hover:from-purple-500 dark:hover:to-cyan-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
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
                'Create account'
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

        {/* Privacy Notice */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-6 text-center text-sm text-gray-500 dark:text-slate-500"
        >
          🔒 Your votes are anonymous and cannot be traced back to you
        </motion.p>
      </motion.div>
    </div>
  );
}
