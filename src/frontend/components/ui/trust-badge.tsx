'use client';

import { motion } from 'framer-motion';
import { ShieldCheckIcon, LockClosedIcon, EyeSlashIcon, CheckBadgeIcon } from '@heroicons/react/24/solid';

interface TrustBadgeProps {
  variant: 'privacy' | 'verified' | 'secure' | 'anonymous';
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

const variants = {
  privacy: {
    icon: EyeSlashIcon,
    label: 'Privacy Protected',
    color: 'text-trust-500',
    bg: 'bg-trust-100 dark:bg-trust-900/30',
    border: 'border-trust-200 dark:border-trust-800',
  },
  verified: {
    icon: CheckBadgeIcon,
    label: 'Verified',
    color: 'text-primary-500',
    bg: 'bg-primary-100 dark:bg-primary-900/30',
    border: 'border-primary-200 dark:border-primary-800',
  },
  secure: {
    icon: ShieldCheckIcon,
    label: 'Secure',
    color: 'text-trust-600',
    bg: 'bg-trust-100 dark:bg-trust-900/30',
    border: 'border-trust-200 dark:border-trust-800',
  },
  anonymous: {
    icon: LockClosedIcon,
    label: 'Anonymous',
    color: 'text-purple-500',
    bg: 'bg-purple-100 dark:bg-purple-900/30',
    border: 'border-purple-200 dark:border-purple-800',
  },
};

const sizes = {
  sm: { icon: 'h-3 w-3', text: 'text-xs', padding: 'px-1.5 py-0.5' },
  md: { icon: 'h-4 w-4', text: 'text-sm', padding: 'px-2 py-1' },
  lg: { icon: 'h-5 w-5', text: 'text-base', padding: 'px-3 py-1.5' },
};

export function TrustBadge({ variant, size = 'md', showLabel = true }: TrustBadgeProps) {
  const config = variants[variant];
  const sizeConfig = sizes[size];
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`inline-flex items-center gap-1 ${sizeConfig.padding} ${config.bg} ${config.border} border rounded-full`}
    >
      <Icon className={`${sizeConfig.icon} ${config.color}`} />
      {showLabel && (
        <span className={`${sizeConfig.text} font-medium ${config.color}`}>
          {config.label}
        </span>
      )}
    </motion.div>
  );
}

// Trust banner for sections
interface TrustBannerProps {
  className?: string;
}

export function TrustBanner({ className = '' }: TrustBannerProps) {
  const trustPoints = [
    { icon: ShieldCheckIcon, text: 'End-to-end encrypted' },
    { icon: EyeSlashIcon, text: 'Anonymous voting' },
    { icon: LockClosedIcon, text: 'No data selling' },
    { icon: CheckBadgeIcon, text: 'Open source' },
  ];

  return (
    <div className={`bg-gradient-to-r from-trust-50 to-primary-50 dark:from-trust-900/20 dark:to-primary-900/20 ${className}`}>
      <div className="mx-auto max-w-7xl px-4 py-3">
        <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
          {trustPoints.map((point, index) => (
            <motion.div
              key={point.text}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300"
            >
              <point.icon className="h-4 w-4 text-trust-500" />
              <span>{point.text}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
