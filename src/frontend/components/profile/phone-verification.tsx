'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  PhoneIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  DevicePhoneMobileIcon,
  ChatBubbleLeftIcon,
} from '@heroicons/react/24/outline';
import { CheckCircleIcon as CheckCircleSolidIcon } from '@heroicons/react/24/solid';
import { api, PhoneVerificationResponse } from '@/lib/api';

interface PhoneVerificationProps {
  phoneNumber?: string;
  phoneVerified: boolean;
  onUpdate?: () => void;
}

type Step = 'add' | 'verify' | 'complete';

export function PhoneVerification({ phoneNumber, phoneVerified, onUpdate }: PhoneVerificationProps) {
  const [step, setStep] = useState<Step>(phoneVerified ? 'complete' : phoneNumber ? 'verify' : 'add');
  const [phone, setPhone] = useState(phoneNumber || '');
  const [code, setCode] = useState(['', '', '', '', '', '']);
  const [error, setError] = useState<string | null>(null);
  const codeInputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const queryClient = useQueryClient();

  // Format phone number for display
  const formatPhoneDisplay = (number: string) => {
    if (!number) return '';
    // Show only last 4 digits
    const cleaned = number.replace(/\D/g, '');
    if (cleaned.length >= 4) {
      return `***-***-${cleaned.slice(-4)}`;
    }
    return number;
  };

  // Add phone number mutation
  const addPhoneMutation = useMutation({
    mutationFn: (phoneNumber: string) => api.addPhoneNumber(phoneNumber),
    onSuccess: (data: PhoneVerificationResponse) => {
      if (data.success) {
        setStep('verify');
        setError(null);
      }
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to send verification code');
    },
  });

  // Verify code mutation
  const verifyMutation = useMutation({
    mutationFn: (code: string) => api.verifyPhoneNumber(code),
    onSuccess: (data: PhoneVerificationResponse) => {
      if (data.phone_verified) {
        setStep('complete');
        setError(null);
        queryClient.invalidateQueries({ queryKey: ['user-profile'] });
        onUpdate?.();
      }
    },
    onError: (err: Error) => {
      setError(err.message || 'Invalid verification code');
      setCode(['', '', '', '', '', '']);
      codeInputRefs.current[0]?.focus();
    },
  });

  // Resend code mutation
  const resendMutation = useMutation({
    mutationFn: () => api.resendVerificationCode(),
    onSuccess: () => {
      setError(null);
      setCode(['', '', '', '', '', '']);
      codeInputRefs.current[0]?.focus();
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to resend code');
    },
  });

  // Remove phone mutation
  const removeMutation = useMutation({
    mutationFn: () => api.removePhoneNumber(),
    onSuccess: () => {
      setPhone('');
      setCode(['', '', '', '', '', '']);
      setStep('add');
      setError(null);
      queryClient.invalidateQueries({ queryKey: ['user-profile'] });
      onUpdate?.();
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to remove phone number');
    },
  });

  const handlePhoneSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (phone.length >= 10) {
      addPhoneMutation.mutate(phone);
    }
  };

  const handleCodeChange = (index: number, value: string) => {
    if (value.length > 1) {
      // Handle paste
      const digits = value.replace(/\D/g, '').slice(0, 6).split('');
      const newCode = [...code];
      digits.forEach((digit, i) => {
        if (index + i < 6) {
          newCode[index + i] = digit;
        }
      });
      setCode(newCode);
      
      // Focus next empty or last input
      const nextIndex = Math.min(index + digits.length, 5);
      codeInputRefs.current[nextIndex]?.focus();
      
      // Auto-submit if complete
      if (newCode.every(d => d !== '')) {
        verifyMutation.mutate(newCode.join(''));
      }
      return;
    }

    if (!/^\d*$/.test(value)) return;

    const newCode = [...code];
    newCode[index] = value;
    setCode(newCode);

    // Auto-focus next input
    if (value && index < 5) {
      codeInputRefs.current[index + 1]?.focus();
    }

    // Auto-submit when complete
    if (newCode.every(d => d !== '')) {
      verifyMutation.mutate(newCode.join(''));
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      codeInputRefs.current[index - 1]?.focus();
    }
  };

  // Focus first code input when moving to verify step
  useEffect(() => {
    if (step === 'verify') {
      codeInputRefs.current[0]?.focus();
    }
  }, [step]);

  return (
    <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-gray-200 dark:border-slate-700/50 p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary-100 dark:bg-cyan-500/20 rounded-lg">
          <DevicePhoneMobileIcon className="h-6 w-6 text-primary-600 dark:text-cyan-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Phone Number</h3>
          <p className="text-sm text-gray-600 dark:text-slate-400">Receive daily polls via SMS</p>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {/* Step 1: Add Phone Number */}
        {step === 'add' && (
          <motion.form
            key="add"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            onSubmit={handlePhoneSubmit}
            className="space-y-4"
          >
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
                Phone Number
              </label>
              <div className="relative">
                <PhoneIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 dark:text-slate-500" />
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+1 (555) 123-4567"
                  className="w-full pl-10 pr-4 py-3 bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:focus:ring-cyan-500 focus:border-transparent"
                />
              </div>
              <p className="text-xs text-gray-500 dark:text-slate-500 mt-2">
                We&apos;ll send a verification code to this number
              </p>
            </div>

            {error && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-2 text-red-500 dark:text-red-400 text-sm"
              >
                <XCircleIcon className="h-4 w-4" />
                {error}
              </motion.div>
            )}

            <button
              type="submit"
              disabled={phone.length < 10 || addPhoneMutation.isPending}
              className="w-full py-3 bg-gradient-to-r from-primary-600 to-accent-600 dark:from-cyan-600 dark:to-purple-600 text-white font-medium rounded-lg hover:from-primary-500 hover:to-accent-500 dark:hover:from-cyan-500 dark:hover:to-purple-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {addPhoneMutation.isPending ? (
                <>
                  <ArrowPathIcon className="h-5 w-5 animate-spin" />
                  Sending code...
                </>
              ) : (
                <>
                  <ChatBubbleLeftIcon className="h-5 w-5" />
                  Send Verification Code
                </>
              )}
            </button>
          </motion.form>
        )}

        {/* Step 2: Verify Code */}
        {step === 'verify' && (
          <motion.div
            key="verify"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-6"
          >
            <div className="text-center">
              <p className="text-gray-700 dark:text-slate-300 mb-1">Enter the 6-digit code sent to</p>
              <p className="text-gray-900 dark:text-white font-medium">{formatPhoneDisplay(phone)}</p>
            </div>

            <div className="flex justify-center gap-2">
              {code.map((digit, index) => (
                <input
                  key={index}
                  ref={(el) => { codeInputRefs.current[index] = el; }}
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={digit}
                  onChange={(e) => handleCodeChange(index, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(index, e)}
                  className="w-12 h-14 text-center text-2xl font-bold bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500 dark:focus:ring-cyan-500 focus:border-transparent"
                />
              ))}
            </div>

            {error && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center justify-center gap-2 text-red-500 dark:text-red-400 text-sm"
              >
                <XCircleIcon className="h-4 w-4" />
                {error}
              </motion.div>
            )}

            {verifyMutation.isPending && (
              <div className="flex justify-center">
                <ArrowPathIcon className="h-6 w-6 text-primary-500 dark:text-cyan-400 animate-spin" />
              </div>
            )}

            <div className="flex items-center justify-center gap-4 text-sm">
              <button
                onClick={() => resendMutation.mutate()}
                disabled={resendMutation.isPending}
                className="text-primary-600 dark:text-cyan-400 hover:text-primary-500 dark:hover:text-cyan-300 transition-colors disabled:opacity-50"
              >
                {resendMutation.isPending ? 'Sending...' : 'Resend code'}
              </button>
              <span className="text-gray-400 dark:text-slate-600">•</span>
              <button
                onClick={() => {
                  setStep('add');
                  setCode(['', '', '', '', '', '']);
                  setError(null);
                }}
                className="text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300 transition-colors"
              >
                Change number
              </button>
            </div>
          </motion.div>
        )}

        {/* Step 3: Verified */}
        {step === 'complete' && (
          <motion.div
            key="complete"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-4"
          >
            <div className="flex items-center justify-between p-4 bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/30 rounded-lg">
              <div className="flex items-center gap-3">
                <CheckCircleSolidIcon className="h-6 w-6 text-green-500 dark:text-green-400" />
                <div>
                  <p className="text-gray-900 dark:text-white font-medium">Phone Verified</p>
                  <p className="text-gray-600 dark:text-slate-400 text-sm">{formatPhoneDisplay(phoneNumber || phone)}</p>
                </div>
              </div>
              <CheckCircleIcon className="h-5 w-5 text-green-500 dark:text-green-400" />
            </div>

            <button
              onClick={() => removeMutation.mutate()}
              disabled={removeMutation.isPending}
              className="w-full py-2 text-red-500 dark:text-red-400 hover:text-red-600 dark:hover:text-red-300 text-sm transition-colors disabled:opacity-50"
            >
              {removeMutation.isPending ? 'Removing...' : 'Remove phone number'}
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
