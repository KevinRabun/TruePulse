'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  BellIcon,
  ChatBubbleBottomCenterTextIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { api } from '@/lib/api';

interface SMSPreferencesProps {
  smsNotifications: boolean;
  dailyPollSms: boolean;
  phoneVerified: boolean;
  onUpdate?: () => void;
}

export function SMSPreferences({
  smsNotifications: initialSmsNotifications,
  dailyPollSms: initialDailyPollSms,
  phoneVerified,
  onUpdate,
}: SMSPreferencesProps) {
  const [smsNotifications, setSmsNotifications] = useState(initialSmsNotifications);
  const [dailyPollSms, setDailyPollSms] = useState(initialDailyPollSms);
  const queryClient = useQueryClient();

  // Sync with props when they change
  useEffect(() => {
    setSmsNotifications(initialSmsNotifications);
    setDailyPollSms(initialDailyPollSms);
  }, [initialSmsNotifications, initialDailyPollSms]);

  const updateMutation = useMutation({
    mutationFn: (data: { sms_notifications: boolean; daily_poll_sms: boolean }) =>
      api.updateSmsPreferences(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-profile'] });
      onUpdate?.();
    },
  });

  const handleSmsNotificationsChange = (enabled: boolean) => {
    setSmsNotifications(enabled);
    // If disabling all SMS notifications, also disable daily polls
    const newDailyPollSms = enabled ? dailyPollSms : false;
    if (!enabled) {
      setDailyPollSms(false);
    }
    updateMutation.mutate({
      sms_notifications: enabled,
      daily_poll_sms: newDailyPollSms,
    });
  };

  const handleDailyPollSmsChange = (enabled: boolean) => {
    setDailyPollSms(enabled);
    updateMutation.mutate({
      sms_notifications: smsNotifications,
      daily_poll_sms: enabled,
    });
  };

  if (!phoneVerified) {
    return (
      <div className="bg-gray-100 dark:bg-slate-800/50 rounded-xl border border-gray-200 dark:border-slate-700/50 p-6 opacity-50">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-gray-200 dark:bg-slate-700/50 rounded-lg">
            <BellIcon className="h-6 w-6 text-gray-400 dark:text-slate-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-500 dark:text-slate-400">SMS Preferences</h3>
            <p className="text-sm text-gray-400 dark:text-slate-500">Verify your phone number to enable SMS</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-gray-200 dark:border-slate-700/50 p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-accent-100 dark:bg-purple-500/20 rounded-lg">
          <BellIcon className="h-6 w-6 text-accent-600 dark:text-purple-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">SMS Preferences</h3>
          <p className="text-sm text-gray-600 dark:text-slate-400">Manage your SMS notification settings</p>
        </div>
      </div>

      <div className="space-y-4">
        {/* Master SMS toggle */}
        <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-slate-900/30 rounded-lg">
          <div className="flex items-center gap-3">
            <ChatBubbleBottomCenterTextIcon className="h-5 w-5 text-gray-400 dark:text-slate-400" />
            <div>
              <p className="text-gray-900 dark:text-white font-medium">SMS Notifications</p>
              <p className="text-sm text-gray-600 dark:text-slate-400">Receive notifications via text message</p>
            </div>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={smsNotifications}
              onChange={(e) => handleSmsNotificationsChange(e.target.checked)}
              disabled={updateMutation.isPending}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-300 dark:bg-slate-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-accent-500 dark:peer-focus:ring-purple-500 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-gradient-to-r peer-checked:from-primary-600 peer-checked:to-accent-600 dark:peer-checked:from-purple-600 dark:peer-checked:to-cyan-600"></div>
          </label>
        </div>

        {/* Daily Poll SMS toggle */}
        <motion.div
          initial={false}
          animate={{
            opacity: smsNotifications ? 1 : 0.5,
            y: smsNotifications ? 0 : 5,
          }}
          className="flex items-center justify-between p-4 bg-gray-50 dark:bg-slate-900/30 rounded-lg"
        >
          <div className="flex items-center gap-3">
            <ClockIcon className="h-5 w-5 text-gray-400 dark:text-slate-400" />
            <div>
              <p className="text-gray-900 dark:text-white font-medium">Daily Poll Reminders</p>
              <p className="text-sm text-gray-600 dark:text-slate-400">Get a daily SMS with the poll link</p>
            </div>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={dailyPollSms}
              onChange={(e) => handleDailyPollSmsChange(e.target.checked)}
              disabled={!smsNotifications || updateMutation.isPending}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-300 dark:bg-slate-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-accent-500 dark:peer-focus:ring-purple-500 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-gradient-to-r peer-checked:from-primary-600 peer-checked:to-accent-600 dark:peer-checked:from-purple-600 dark:peer-checked:to-cyan-600 peer-disabled:cursor-not-allowed"></div>
          </label>
        </motion.div>

        {dailyPollSms && smsNotifications && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="p-4 bg-primary-50 dark:bg-cyan-500/10 border border-primary-200 dark:border-cyan-500/30 rounded-lg"
          >
            <p className="text-primary-700 dark:text-cyan-200 text-sm">
              🎯 You&apos;ll receive a text message each day when a new poll is available.
              Messages are sent around 9:00 AM in your local timezone.
            </p>
          </motion.div>
        )}
      </div>

      {updateMutation.isPending && (
        <div className="mt-4 text-center text-sm text-gray-500 dark:text-slate-400">
          Saving preferences...
        </div>
      )}
    </div>
  );
}
