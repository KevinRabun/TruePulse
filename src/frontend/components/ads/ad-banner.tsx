'use client';

import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { XMarkIcon, SparklesIcon, HeartIcon } from '@heroicons/react/24/outline';
import { useAds } from './ad-context';

export type AdSize = 'banner' | 'leaderboard' | 'rectangle' | 'skyscraper';
export type AdPlacement = 'header' | 'footer' | 'sidebar' | 'between-content' | 'inline';

interface AdBannerProps {
  size?: AdSize;
  placement: AdPlacement;
  className?: string;
  showCloseButton?: boolean;
  onClose?: () => void;
}

// Standard IAB ad sizes
const adSizes: Record<AdSize, { width: number; height: number; className: string }> = {
  banner: { width: 468, height: 60, className: 'w-full max-w-[468px] h-[60px]' },
  leaderboard: { width: 728, height: 90, className: 'w-full max-w-[728px] h-[90px]' },
  rectangle: { width: 300, height: 250, className: 'w-full max-w-[300px] h-[250px]' },
  skyscraper: { width: 160, height: 600, className: 'w-[160px] h-[600px]' },
};

export function AdBanner({ 
  size = 'banner', 
  placement, 
  className = '', 
  showCloseButton = false,
  onClose 
}: AdBannerProps) {
  const { trackView, trackClick } = useAds();
  const hasTrackedView = useRef(false);
  const [isVisible, setIsVisible] = useState(true);
  const adRef = useRef<HTMLDivElement>(null);

  // Track view when ad becomes visible
  useEffect(() => {
    if (!hasTrackedView.current && isVisible) {
      hasTrackedView.current = true;
      trackView(size, placement);
    }
  }, [isVisible, size, placement, trackView]);

  // Intersection Observer to track when ad is in viewport
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !hasTrackedView.current) {
            hasTrackedView.current = true;
            trackView(size, placement);
          }
        });
      },
      { threshold: 0.5 }
    );

    if (adRef.current) {
      observer.observe(adRef.current);
    }

    return () => observer.disconnect();
  }, [size, placement, trackView]);

  const handleClick = () => {
    trackClick(size, placement);
    // In production, this would navigate to the ad destination
    // For now, we'll just track the click
  };

  const handleClose = () => {
    setIsVisible(false);
    onClose?.();
  };

  if (!isVisible) return null;

  const sizeConfig = adSizes[size];

  return (
    <motion.div
      ref={adRef}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className={`relative ${className}`}
    >
      {/* Ad Container - Placeholder for real ad content */}
      <div 
        onClick={handleClick}
        className={`${sizeConfig.className} mx-auto bg-linear-to-br from-gray-100 to-gray-200 dark:from-slate-800 dark:to-slate-700 rounded-lg border border-gray-200 dark:border-slate-600 flex items-center justify-center cursor-pointer hover:opacity-90 transition-opacity relative overflow-hidden group`}
      >
        {/* Sponsor Indicator */}
        <div className="absolute top-1 left-1 px-1.5 py-0.5 bg-gray-500/20 dark:bg-slate-500/30 rounded text-[10px] text-gray-500 dark:text-slate-400 font-medium">
          Sponsored
        </div>

        {/* Close Button */}
        {showCloseButton && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleClose();
            }}
            className="absolute top-1 right-1 p-1 bg-gray-500/20 dark:bg-slate-500/30 rounded-full text-gray-500 dark:text-slate-400 hover:bg-gray-500/40 dark:hover:bg-slate-500/50 transition-colors z-10"
            aria-label="Close ad"
          >
            <XMarkIcon className="h-3 w-3" />
          </button>
        )}

        {/* Placeholder Content */}
        <div className="flex flex-col items-center justify-center text-center p-2">
          <div className="flex items-center gap-1 text-gray-400 dark:text-slate-500 mb-1">
            <SparklesIcon className="h-4 w-4" />
            <span className="text-xs">Ad Space</span>
          </div>
          <p className="text-[10px] text-gray-400 dark:text-slate-500">
            Your ad here supports TruePulse
          </p>
        </div>

        {/* Hover Effect */}
        <div className="absolute inset-0 bg-linear-to-r from-primary-500/0 via-primary-500/5 to-accent-500/0 opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>

      {/* Support Message */}
      <div className="flex items-center justify-center gap-1 mt-1">
        <HeartIcon className="h-3 w-3 text-pink-400" />
        <span className="text-[10px] text-gray-400 dark:text-slate-500">
          Ads help keep TruePulse free
        </span>
      </div>
    </motion.div>
  );
}

// Responsive wrapper that adjusts size based on screen width
export function ResponsiveAdBanner({ 
  placement,
  className = '',
  showCloseButton = false,
  onClose 
}: Omit<AdBannerProps, 'size'>) {
  const [size, setSize] = useState<AdSize>('banner');

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      if (width >= 768) {
        setSize('leaderboard');
      } else {
        setSize('banner');
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <AdBanner 
      size={size} 
      placement={placement} 
      className={className}
      showCloseButton={showCloseButton}
      onClose={onClose}
    />
  );
}
