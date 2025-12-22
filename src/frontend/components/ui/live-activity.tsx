'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useState } from 'react';
import { GlobeAltIcon, UsersIcon, SparklesIcon } from '@heroicons/react/24/outline';
import { api } from '@/lib/api';

interface LiveActivityIndicatorProps {
  className?: string;
  variant?: 'compact' | 'expanded';
}

// Activity notifications (region activity is illustrative based on global reach)
const regions = ['North America', 'Europe', 'Asia', 'South America', 'Africa', 'Oceania'];
const activities = [
  'voted on a poll',
  'joined the community',
  'earned an achievement',
  'completed a streak',
];

function generateActivity() {
  return {
    id: Date.now() + Math.random(),
    region: regions[Math.floor(Math.random() * regions.length)],
    activity: activities[Math.floor(Math.random() * activities.length)],
  };
}

export function LiveActivityIndicator({ className = '', variant = 'compact' }: LiveActivityIndicatorProps) {
  const [activeUsers, setActiveUsers] = useState<number | null>(null);
  const [recentActivity, setRecentActivity] = useState(generateActivity());
  const [showActivity, setShowActivity] = useState(false);

  useEffect(() => {
    // Fetch real stats from API
    const fetchStats = async () => {
      try {
        const response = await api.getPlatformStats();
        setActiveUsers(response.stats.active_users_raw);
      } catch (error) {
        console.error('Failed to fetch platform stats:', error);
        // Fallback to a reasonable estimate if API fails
        setActiveUsers(null);
      }
    };

    fetchStats();
    
    // Refresh stats periodically
    const statsInterval = setInterval(fetchStats, 60000); // Every minute

    // Show activity notifications periodically
    const activityInterval = setInterval(() => {
      setRecentActivity(generateActivity());
      setShowActivity(true);
      setTimeout(() => setShowActivity(false), 3000);
    }, 8000);

    // Initial activity
    setTimeout(() => {
      setShowActivity(true);
      setTimeout(() => setShowActivity(false), 3000);
    }, 2000);

    return () => {
      clearInterval(statsInterval);
      clearInterval(activityInterval);
    };
  }, []);

  if (variant === 'compact') {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-trust-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-trust-500" />
        </span>
        <span className="text-sm text-gray-600 dark:text-gray-400">
          <span className="font-semibold text-gray-900 dark:text-white">
            {activeUsers !== null ? activeUsers.toLocaleString() : '—'}
          </span>{' '}
          active now
        </span>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      {/* Main indicator */}
      <div className="flex items-center gap-4 px-4 py-3 bg-white/80 dark:bg-gray-800/80 backdrop-blur-xs rounded-xl shadow-xs border border-gray-200 dark:border-gray-700">
        {/* Live pulse */}
        <div className="relative">
          <GlobeAltIcon className="h-8 w-8 text-primary-500" />
          <span className="absolute -top-1 -right-1 flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-trust-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-trust-500" />
          </span>
        </div>
        
        <div>
          <div className="flex items-center gap-2">
            <UsersIcon className="h-4 w-4 text-gray-500" />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              <motion.span
                key={activeUsers ?? 0}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="font-bold text-gray-900 dark:text-white"
              >
                {activeUsers !== null ? activeUsers.toLocaleString() : '---'}
              </motion.span>{' '}
              people voting worldwide
            </span>
          </div>
          
          {/* Recent activity ticker */}
          <AnimatePresence mode="wait">
            {showActivity && (
              <motion.div
                key={recentActivity.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex items-center gap-1 mt-1 text-xs text-gray-500 dark:text-gray-400"
              >
                <SparklesIcon className="h-3 w-3 text-warm-500" />
                <span>
                  Someone {recentActivity.activity} <span className="font-medium">{recentActivity.region}</span>
                </span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

// Floating version for hero sections
export function FloatingActivityBadge({ className = '' }: { className?: string }) {
  const [activeUsers, setActiveUsers] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await api.getPlatformStats();
        setActiveUsers(response.stats.active_users_raw);
      } catch (error) {
        console.error('Failed to fetch platform stats:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
    
    // Refresh periodically
    const interval = setInterval(fetchStats, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`inline-flex items-center gap-2 px-4 py-2 bg-white/90 dark:bg-gray-800/90 backdrop-blur-xs rounded-full shadow-lg border border-gray-200 dark:border-gray-700 ${className}`}
    >
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-trust-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-trust-500" />
      </span>
      <span className="text-sm font-medium text-gray-900 dark:text-white">
        {isLoading ? (
          <span className="animate-pulse">Loading...</span>
        ) : activeUsers !== null ? (
          `${activeUsers.toLocaleString()}+ active now`
        ) : (
          'Users active now'
        )}
      </span>
    </motion.div>
  );
}
