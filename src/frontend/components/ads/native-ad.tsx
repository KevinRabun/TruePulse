'use client';

import { motion } from 'framer-motion';
import { SparklesIcon, HeartIcon } from '@heroicons/react/24/outline';
import { useAds } from './ad-context';
import { useRef, useEffect } from 'react';

interface NativeAdProps {
  placement: string;
  className?: string;
}

/**
 * Native ad component that blends with surrounding content
 * Designed to appear between poll cards or content items
 * Non-intrusive and clearly labeled as sponsored
 */
export function NativeAd({ placement, className = '' }: NativeAdProps) {
  const { trackView, trackClick } = useAds();
  const hasTrackedView = useRef(false);
  const adRef = useRef<HTMLDivElement>(null);

  // Intersection Observer to track when ad is in viewport
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !hasTrackedView.current) {
            hasTrackedView.current = true;
            trackView('native', placement);
          }
        });
      },
      { threshold: 0.5 }
    );

    if (adRef.current) {
      observer.observe(adRef.current);
    }

    return () => observer.disconnect();
  }, [placement, trackView]);

  const handleClick = () => {
    trackClick('native', placement);
  };

  return (
    <motion.div
      ref={adRef}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={handleClick}
      className={`bg-linear-to-br from-gray-50 to-gray-100 dark:from-slate-800/50 dark:to-slate-700/50 rounded-xl border border-gray-200 dark:border-slate-600/50 p-6 cursor-pointer hover:shadow-md transition-shadow ${className}`}
    >
      {/* Sponsored Label */}
      <div className="flex items-center gap-2 mb-3">
        <SparklesIcon className="h-4 w-4 text-amber-500" />
        <span className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
          Sponsored
        </span>
      </div>

      {/* Ad Content Placeholder */}
      <div className="flex items-start gap-4">
        {/* Image Placeholder */}
        <div className="w-16 h-16 rounded-lg bg-linear-to-br from-primary-100 to-accent-100 dark:from-purple-900/30 dark:to-cyan-900/30 flex items-center justify-center shrink-0">
          <SparklesIcon className="h-8 w-8 text-primary-400 dark:text-purple-400" />
        </div>

        {/* Text Content */}
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-800 dark:text-slate-200 mb-1 line-clamp-1">
            Featured Partner
          </h3>
          <p className="text-sm text-gray-600 dark:text-slate-400 line-clamp-2">
            Your message could reach engaged voters. Partner with TruePulse.
          </p>
        </div>
      </div>

      {/* CTA */}
      <div className="mt-4 flex items-center justify-between">
        <span className="text-xs text-primary-600 dark:text-cyan-400 font-medium">
          Learn More →
        </span>
        <div className="flex items-center gap-1">
          <HeartIcon className="h-3 w-3 text-pink-400" />
          <span className="text-[10px] text-gray-400 dark:text-slate-500">
            Supports TruePulse
          </span>
        </div>
      </div>
    </motion.div>
  );
}

/**
 * Compact native ad for inline placement
 */
export function CompactNativeAd({ placement, className = '' }: NativeAdProps) {
  const { trackView, trackClick } = useAds();
  const hasTrackedView = useRef(false);
  const adRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !hasTrackedView.current) {
            hasTrackedView.current = true;
            trackView('native-compact', placement);
          }
        });
      },
      { threshold: 0.5 }
    );

    if (adRef.current) {
      observer.observe(adRef.current);
    }

    return () => observer.disconnect();
  }, [placement, trackView]);

  const handleClick = () => {
    trackClick('native-compact', placement);
  };

  return (
    <motion.div
      ref={adRef}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      onClick={handleClick}
      className={`flex items-center gap-3 p-3 bg-gray-50 dark:bg-slate-800/30 rounded-lg border border-gray-200 dark:border-slate-700/50 cursor-pointer hover:bg-gray-100 dark:hover:bg-slate-700/50 transition-colors ${className}`}
    >
      <SparklesIcon className="h-5 w-5 text-amber-500 shrink-0" />
      <div className="flex-1 min-w-0">
        <span className="text-xs text-gray-500 dark:text-slate-400">
          <span className="font-medium">Sponsored</span> · Partner with TruePulse
        </span>
      </div>
      <span className="text-xs text-primary-600 dark:text-cyan-400">→</span>
    </motion.div>
  );
}
