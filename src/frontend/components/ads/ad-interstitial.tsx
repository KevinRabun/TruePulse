'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { XMarkIcon, SparklesIcon, HeartIcon, GiftIcon } from '@heroicons/react/24/outline';
import { useAds } from './ad-context';

interface AdInterstitialProps {
  isOpen: boolean;
  onClose: () => void;
  // Time in seconds before user can skip (0 = no skip button)
  skipDelay?: number;
  // Optional reward for watching full ad
  onReward?: () => void;
  rewardDescription?: string;
}

export function AdInterstitial({
  isOpen,
  onClose,
  skipDelay = 3,
  onReward,
  rewardDescription = 'Bonus points',
}: AdInterstitialProps) {
  const { trackView, trackClick } = useAds();
  const [canSkip, setCanSkip] = useState(false);
  const [countdown, setCountdown] = useState(skipDelay);
  const [hasWatchedFull, setHasWatchedFull] = useState(false);

  // Track view when interstitial opens
  useEffect(() => {
    if (isOpen) {
      trackView('interstitial', 'fullscreen');
      setCanSkip(false);
      setCountdown(skipDelay);
      setHasWatchedFull(false);
    }
  }, [isOpen, skipDelay, trackView]);

  // Countdown timer
  useEffect(() => {
    if (!isOpen) return;

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          setCanSkip(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isOpen]);

  // Full watch timer (10 seconds)
  useEffect(() => {
    if (!isOpen) return;

    const fullWatchTimer = setTimeout(() => {
      setHasWatchedFull(true);
    }, 10000);

    return () => clearTimeout(fullWatchTimer);
  }, [isOpen]);

  const handleClose = useCallback(() => {
    if (hasWatchedFull && onReward) {
      onReward();
    }
    onClose();
  }, [hasWatchedFull, onReward, onClose]);

  const handleClick = () => {
    trackClick('interstitial', 'fullscreen');
    // In production, navigate to ad destination
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="relative w-full max-w-lg mx-4"
          >
            {/* Ad Content */}
            <div
              onClick={handleClick}
              className="bg-gradient-to-br from-gray-100 to-gray-200 dark:from-slate-800 dark:to-slate-700 rounded-2xl border border-gray-200 dark:border-slate-600 overflow-hidden cursor-pointer"
            >
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-2 bg-gray-200/50 dark:bg-slate-700/50 border-b border-gray-200 dark:border-slate-600">
                <div className="flex items-center gap-2">
                  <SparklesIcon className="h-4 w-4 text-gray-500 dark:text-slate-400" />
                  <span className="text-xs text-gray-500 dark:text-slate-400 font-medium">
                    Sponsored
                  </span>
                </div>
                
                {/* Skip/Close Button */}
                {canSkip ? (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleClose();
                    }}
                    className="flex items-center gap-1 px-3 py-1 bg-gray-300 dark:bg-slate-600 rounded-full text-xs font-medium text-gray-700 dark:text-slate-300 hover:bg-gray-400 dark:hover:bg-slate-500 transition-colors"
                  >
                    <XMarkIcon className="h-3 w-3" />
                    {hasWatchedFull ? 'Claim & Close' : 'Skip'}
                  </button>
                ) : (
                  <span className="px-3 py-1 bg-gray-300 dark:bg-slate-600 rounded-full text-xs font-medium text-gray-700 dark:text-slate-300">
                    Skip in {countdown}s
                  </span>
                )}
              </div>

              {/* Main Ad Area - Placeholder */}
              <div className="aspect-video flex items-center justify-center p-8">
                <div className="text-center">
                  <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-primary-500/20 to-accent-500/20 dark:from-purple-500/20 dark:to-cyan-500/20 flex items-center justify-center">
                    <SparklesIcon className="h-10 w-10 text-primary-500 dark:text-purple-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-700 dark:text-slate-300 mb-2">
                    Ad Placeholder
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-slate-400">
                    Premium ad content would appear here
                  </p>
                </div>
              </div>

              {/* Reward Indicator */}
              {onReward && (
                <div className="px-4 py-3 bg-gradient-to-r from-amber-100 to-yellow-100 dark:from-amber-900/30 dark:to-yellow-900/30 border-t border-amber-200 dark:border-amber-800/50">
                  <div className="flex items-center justify-center gap-2">
                    <GiftIcon className={`h-5 w-5 ${hasWatchedFull ? 'text-amber-500' : 'text-amber-400/50'}`} />
                    <span className={`text-sm font-medium ${hasWatchedFull ? 'text-amber-700 dark:text-amber-400' : 'text-amber-500/50 dark:text-amber-500/50'}`}>
                      {hasWatchedFull 
                        ? `🎉 ${rewardDescription} earned!` 
                        : `Watch full ad for ${rewardDescription}`
                      }
                    </span>
                  </div>
                </div>
              )}

              {/* Footer */}
              <div className="px-4 py-2 bg-gray-200/30 dark:bg-slate-700/30 border-t border-gray-200 dark:border-slate-600">
                <div className="flex items-center justify-center gap-1">
                  <HeartIcon className="h-3 w-3 text-pink-400" />
                  <span className="text-[10px] text-gray-400 dark:text-slate-500">
                    Ads help keep TruePulse free for everyone
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// Hook to manage interstitial display logic
export function useInterstitialAd() {
  const [isOpen, setIsOpen] = useState(false);
  const [frequency, setFrequency] = useState(0); // Track how many actions since last ad

  const showInterstitial = useCallback(() => {
    setIsOpen(true);
  }, []);

  const closeInterstitial = useCallback(() => {
    setIsOpen(false);
    setFrequency(0);
  }, []);

  // Call this after user actions (e.g., votes) to potentially show an ad
  const trackAction = useCallback((threshold: number = 5) => {
    setFrequency((prev) => {
      const newFreq = prev + 1;
      // Show interstitial every N actions
      if (newFreq >= threshold) {
        // Don't show immediately - return the count and let caller decide
        return newFreq;
      }
      return newFreq;
    });
  }, []);

  const shouldShowAd = frequency >= 5;

  return {
    isOpen,
    showInterstitial,
    closeInterstitial,
    trackAction,
    shouldShowAd,
    frequency,
  };
}
