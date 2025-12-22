'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import {
  UsersIcon,
  TrophyIcon,
  SparklesIcon,
  ChartBarIcon,
  CheckCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { api, CommunityAchievementProgress, CommunityAchievementEvent } from '@/lib/api';

interface CommunityAchievementsProps {
  showCompleted?: boolean;
}

export function CommunityAchievements({ showCompleted = true }: CommunityAchievementsProps) {
  const [activeTab, setActiveTab] = useState<'active' | 'completed'>('active');

  const { data: activeAchievements, isLoading: loadingActive } = useQuery({
    queryKey: ['community-achievements-active'],
    queryFn: () => api.getActiveCommunityAchievements(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const { data: completedAchievements, isLoading: loadingCompleted } = useQuery({
    queryKey: ['community-achievements-completed'],
    queryFn: () => api.getCompletedCommunityAchievements(),
    enabled: showCompleted,
  });

  return (
    <div className="bg-white dark:bg-slate-800/50 rounded-2xl border border-gray-200 dark:border-slate-700/50 overflow-hidden">
      {/* Header */}
      <div className="p-6 bg-linear-to-r from-purple-500/10 to-blue-500/10 border-b border-gray-200 dark:border-slate-700/50">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-500/20 rounded-lg">
            <UsersIcon className="h-6 w-6 text-purple-500" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
              Community Achievements
            </h2>
            <p className="text-sm text-gray-600 dark:text-slate-400">
              Work together to unlock special rewards
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      {showCompleted && (
        <div className="flex border-b border-gray-200 dark:border-slate-700/50">
          <button
            onClick={() => setActiveTab('active')}
            className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
              activeTab === 'active'
                ? 'text-purple-600 dark:text-purple-400 border-b-2 border-purple-500'
                : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300'
            }`}
          >
            <SparklesIcon className="h-4 w-4 inline mr-1" />
            Active Goals
          </button>
          <button
            onClick={() => setActiveTab('completed')}
            className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
              activeTab === 'completed'
                ? 'text-purple-600 dark:text-purple-400 border-b-2 border-purple-500'
                : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300'
            }`}
          >
            <TrophyIcon className="h-4 w-4 inline mr-1" />
            Completed
          </button>
        </div>
      )}

      {/* Content */}
      <div className="p-4">
        <AnimatePresence mode="wait">
          {activeTab === 'active' ? (
            <motion.div
              key="active"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-4"
            >
              {loadingActive ? (
                <LoadingSkeleton count={3} />
              ) : activeAchievements?.length === 0 ? (
                <EmptyState message="No active community goals right now" />
              ) : (
                activeAchievements?.map((achievement) => (
                  <ActiveAchievementCard
                    key={achievement.achievement.id}
                    achievement={achievement}
                  />
                ))
              )}
            </motion.div>
          ) : (
            <motion.div
              key="completed"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-4"
            >
              {loadingCompleted ? (
                <LoadingSkeleton count={3} />
              ) : completedAchievements?.length === 0 ? (
                <EmptyState message="No completed community achievements yet" />
              ) : (
                completedAchievements?.map((event) => (
                  <CompletedAchievementCard key={event.id} event={event} />
                ))
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function ActiveAchievementCard({
  achievement,
}: {
  achievement: CommunityAchievementProgress;
}) {
  const { achievement: ach, current_count, progress_percentage, participant_count, time_remaining_hours, user_participated } = achievement;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="p-4 bg-linear-to-r from-purple-50 to-blue-50 dark:from-purple-500/10 dark:to-blue-500/10 rounded-xl border border-purple-200 dark:border-purple-500/30"
    >
      <div className="flex items-start gap-3">
        <span className="text-3xl">{ach.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-gray-900 dark:text-white truncate">
              {ach.name}
            </h3>
            {user_participated && (
              <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-400 rounded-full">
                Participating
              </span>
            )}
          </div>
          <p className="text-sm text-gray-600 dark:text-slate-400 mb-3">
            {ach.description}
          </p>

          {/* Progress bar */}
          <div className="relative h-3 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden mb-2">
            <motion.div
              className="absolute inset-y-0 left-0 bg-linear-to-r from-purple-500 to-blue-500 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${Math.min(100, progress_percentage)}%` }}
              transition={{ duration: 1, ease: 'easeOut' }}
            />
          </div>

          {/* Stats */}
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-4">
              <span className="text-gray-600 dark:text-slate-400">
                <ChartBarIcon className="h-4 w-4 inline mr-1" />
                {current_count.toLocaleString()} / {ach.target_count.toLocaleString()}
              </span>
              <span className="text-gray-600 dark:text-slate-400">
                <UsersIcon className="h-4 w-4 inline mr-1" />
                {participant_count.toLocaleString()} participants
              </span>
            </div>
            {time_remaining_hours !== undefined && time_remaining_hours > 0 && (
              <span className="text-amber-600 dark:text-amber-400 font-medium">
                <ClockIcon className="h-4 w-4 inline mr-1" />
                {time_remaining_hours.toFixed(1)}h left
              </span>
            )}
          </div>

          {/* Reward info */}
          <div className="mt-3 pt-3 border-t border-purple-200 dark:border-purple-500/30 flex items-center gap-4 text-sm">
            <span className="text-purple-600 dark:text-purple-400 font-medium">
              🏆 +{ach.points_reward} points
            </span>
            <span className="text-purple-600 dark:text-purple-400 font-medium">
              {ach.badge_icon} Badge
            </span>
            {ach.bonus_multiplier > 1 && (
              <span className="text-amber-600 dark:text-amber-400 font-medium">
                ✨ {ach.bonus_multiplier}x bonus
              </span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function CompletedAchievementCard({
  event,
}: {
  event: CommunityAchievementEvent;
}) {
  const completedDate = event.completed_at
    ? new Date(event.completed_at).toLocaleDateString()
    : 'Unknown';

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`p-4 rounded-xl border ${
        event.user_earned_badge
          ? 'bg-linear-to-r from-green-50 to-emerald-50 dark:from-green-500/10 dark:to-emerald-500/10 border-green-200 dark:border-green-500/30'
          : 'bg-gray-50 dark:bg-slate-800 border-gray-200 dark:border-slate-700/50'
      }`}
    >
      <div className="flex items-center gap-3">
        <span className="text-3xl">{event.achievement_icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-gray-900 dark:text-white truncate">
              {event.achievement_name}
            </h3>
            <CheckCircleIcon className="h-5 w-5 text-green-500" />
          </div>
          <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-slate-400">
            <span>{completedDate}</span>
            <span>{event.participant_count.toLocaleString()} participants</span>
            <span>{event.final_count.toLocaleString()} total</span>
          </div>
          {event.user_earned_badge && (
            <div className="mt-2 flex items-center gap-2">
              <span className="text-2xl">{event.badge_icon}</span>
              <span className="text-green-600 dark:text-green-400 font-medium">
                You earned this badge! +{event.user_earned_points} points
              </span>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function LoadingSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="p-4 bg-gray-100 dark:bg-slate-700 rounded-xl animate-pulse"
        >
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-gray-200 dark:bg-slate-600 rounded-lg" />
            <div className="flex-1">
              <div className="h-5 bg-gray-200 dark:bg-slate-600 rounded w-48 mb-2" />
              <div className="h-4 bg-gray-200 dark:bg-slate-600 rounded w-full mb-3" />
              <div className="h-3 bg-gray-200 dark:bg-slate-600 rounded-full w-full" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-8">
      <UsersIcon className="h-12 w-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
      <p className="text-gray-500 dark:text-slate-400">{message}</p>
    </div>
  );
}

// Compact version for sidebar/widget
export function CommunityAchievementsWidget() {
  const { data: activeAchievements, isLoading } = useQuery({
    queryKey: ['community-achievements-active'],
    queryFn: () => api.getActiveCommunityAchievements(),
    refetchInterval: 30000,
  });

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl p-4 animate-pulse">
        <div className="h-6 bg-gray-200 dark:bg-slate-700 rounded w-32 mb-3" />
        <div className="h-16 bg-gray-200 dark:bg-slate-700 rounded" />
      </div>
    );
  }

  const topAchievement = activeAchievements?.[0];

  if (!topAchievement) {
    return null;
  }

  return (
    <div className="bg-linear-to-r from-purple-500/10 to-blue-500/10 dark:from-purple-500/20 dark:to-blue-500/20 rounded-xl p-4 border border-purple-200 dark:border-purple-500/30">
      <div className="flex items-center gap-2 mb-3">
        <UsersIcon className="h-5 w-5 text-purple-500" />
        <span className="text-sm font-semibold text-purple-700 dark:text-purple-300">
          Community Goal
        </span>
      </div>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-2xl">{topAchievement.achievement.icon}</span>
        <span className="font-medium text-gray-900 dark:text-white text-sm">
          {topAchievement.achievement.name}
        </span>
      </div>
      <div className="relative h-2 bg-purple-200 dark:bg-purple-900/50 rounded-full overflow-hidden">
        <motion.div
          className="absolute inset-y-0 left-0 bg-linear-to-r from-purple-500 to-blue-500 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(100, topAchievement.progress_percentage)}%` }}
          transition={{ duration: 1, ease: 'easeOut' }}
        />
      </div>
      <div className="flex justify-between mt-2 text-xs text-gray-600 dark:text-slate-400">
        <span>{topAchievement.progress_percentage.toFixed(0)}%</span>
        <span>{topAchievement.participant_count} participants</span>
      </div>
    </div>
  );
}
