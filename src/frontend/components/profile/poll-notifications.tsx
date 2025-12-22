'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import {
  BellIcon,
  HeartIcon,
  BoltIcon,
} from '@heroicons/react/24/outline';
import { api, UserSettings } from '@/lib/api';

interface PollNotificationsProps {
  onUpdate?: () => void;
}

export function PollNotifications({ onUpdate }: PollNotificationsProps) {
  const queryClient = useQueryClient();

  // Fetch current settings
  const { data: settings, isLoading } = useQuery({
    queryKey: ['user-settings'],
    queryFn: () => api.getSettings(),
  });

  // Initialize state with default values, then update when settings load
  const [pulseNotifications, setPulseNotifications] = useState(true);
  const [flashNotifications, setFlashNotifications] = useState(true);
  const [flashPollsPerDay, setFlashPollsPerDay] = useState(5);

  // Track if we've synced with server settings
  const [hasSynced, setHasSynced] = useState(false);

  // Sync with fetched settings only once when data first loads
  useEffect(() => {
    if (settings && !hasSynced) {
      setPulseNotifications(settings.pulse_poll_notifications ?? true);
      setFlashNotifications(settings.flash_poll_notifications ?? true);
      setFlashPollsPerDay(settings.flash_polls_per_day ?? 5);
      setHasSynced(true);
    }
  }, [settings, hasSynced]);

  const updateMutation = useMutation({
    mutationFn: (data: Partial<UserSettings>) => api.updateSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-settings'] });
      queryClient.invalidateQueries({ queryKey: ['user-profile'] });
      onUpdate?.();
    },
  });

  const handlePulseChange = (enabled: boolean) => {
    setPulseNotifications(enabled);
    updateMutation.mutate({ pulse_poll_notifications: enabled });
  };

  const handleFlashChange = (enabled: boolean) => {
    setFlashNotifications(enabled);
    updateMutation.mutate({ flash_poll_notifications: enabled });
  };

  const handleFlashPerDayChange = (value: number) => {
    setFlashPollsPerDay(value);
    updateMutation.mutate({ flash_polls_per_day: value });
  };

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-gray-200 dark:border-slate-700/50 p-6 animate-pulse">
        <div className="h-8 bg-gray-200 dark:bg-slate-700 rounded w-48 mb-4"></div>
        <div className="h-24 bg-gray-200 dark:bg-slate-700 rounded"></div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-gray-200 dark:border-slate-700/50 p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary-100 dark:bg-primary-500/20 rounded-lg">
          <BellIcon className="h-6 w-6 text-primary-600 dark:text-primary-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Poll Notifications
          </h3>
          <p className="text-sm text-gray-600 dark:text-slate-400">
            Choose how many polls you want to be notified about
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {/* Pulse Poll Notifications */}
        <div className="flex items-center justify-between p-4 bg-linear-to-r from-rose-50 to-pink-50 dark:from-rose-500/10 dark:to-pink-500/10 rounded-lg border border-rose-200 dark:border-rose-500/30">
          <div className="flex items-center gap-3">
            <HeartIcon className="h-5 w-5 text-rose-500 dark:text-rose-400" />
            <div>
              <p className="text-gray-900 dark:text-white font-medium">
                Daily Pulse Poll
              </p>
              <p className="text-sm text-gray-500 dark:text-slate-400">
                Featured poll every day, 8am-8pm ET
              </p>
            </div>
          </div>
          <motion.button
            whileTap={{ scale: 0.95 }}
            onClick={() => handlePulseChange(!pulseNotifications)}
            disabled={updateMutation.isPending}
            className={`relative w-12 h-6 rounded-full transition-colors duration-200 ${
              pulseNotifications
                ? 'bg-rose-500'
                : 'bg-gray-300 dark:bg-slate-600'
            }`}
          >
            <motion.div
              className="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-sm"
              animate={{ x: pulseNotifications ? 24 : 0 }}
              transition={{ type: 'spring', stiffness: 500, damping: 30 }}
            />
          </motion.button>
        </div>

        {/* Flash Poll Notifications */}
        <div className="p-4 bg-linear-to-r from-amber-50 to-orange-50 dark:from-amber-500/10 dark:to-orange-500/10 rounded-lg border border-amber-200 dark:border-amber-500/30">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <BoltIcon className="h-5 w-5 text-amber-500 dark:text-amber-400" />
              <div>
                <p className="text-gray-900 dark:text-white font-medium">
                  Flash Polls
                </p>
                <p className="text-sm text-gray-500 dark:text-slate-400">
                  Quick 1-hour polls throughout the day
                </p>
              </div>
            </div>
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={() => handleFlashChange(!flashNotifications)}
              disabled={updateMutation.isPending}
              className={`relative w-12 h-6 rounded-full transition-colors duration-200 ${
                flashNotifications
                  ? 'bg-amber-500'
                  : 'bg-gray-300 dark:bg-slate-600'
              }`}
            >
              <motion.div
                className="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-sm"
                animate={{ x: flashNotifications ? 24 : 0 }}
                transition={{ type: 'spring', stiffness: 500, damping: 30 }}
              />
            </motion.button>
          </div>

          {/* Flash polls per day slider */}
          {flashNotifications && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-4 pt-4 border-t border-amber-200 dark:border-amber-500/30"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-600 dark:text-slate-400">
                  Max flash poll notifications per day
                </span>
                <span className="text-sm font-semibold text-amber-600 dark:text-amber-400">
                  {flashPollsPerDay === 0 ? 'None' : flashPollsPerDay === 12 ? 'All (12)' : flashPollsPerDay}
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="12"
                value={flashPollsPerDay}
                onChange={(e) => handleFlashPerDayChange(parseInt(e.target.value))}
                className="w-full h-2 bg-amber-200 dark:bg-amber-900/50 rounded-lg appearance-none cursor-pointer accent-amber-500"
              />
              <div className="flex justify-between text-xs text-gray-400 dark:text-slate-500 mt-1">
                <span>0</span>
                <span>3</span>
                <span>6</span>
                <span>9</span>
                <span>12</span>
              </div>
            </motion.div>
          )}
        </div>

        {/* Info box */}
        <div className="p-4 bg-blue-50 dark:bg-blue-500/10 rounded-lg border border-blue-200 dark:border-blue-500/30">
          <p className="text-sm text-blue-700 dark:text-blue-300">
            <strong>Tip:</strong> Pulse Polls are our daily featured questions on important topics.
            Flash Polls cover breaking news and trending topics throughout the day.
            Participating in both helps improve poll accuracy and earns you bonus achievements!
          </p>
        </div>
      </div>
    </div>
  );
}
