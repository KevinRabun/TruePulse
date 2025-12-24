'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { api, LeaderboardEntry } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import {
  TrophyIcon,
  ChartBarIcon,
  UserCircleIcon,
  ArrowLeftIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import { TrophyIcon as TrophySolidIcon } from '@heroicons/react/24/solid';

type TimeFrame = 'daily' | 'weekly' | 'monthly' | 'all_time';

const timeFrameLabels: Record<TimeFrame, string> = {
  daily: 'Today',
  weekly: 'This Week',
  monthly: 'This Month',
  all_time: 'All Time',
};

const getRankIcon = (rank: number) => {
  switch (rank) {
    case 1:
      return <TrophySolidIcon className="h-6 w-6 text-yellow-400" />;
    case 2:
      return <TrophySolidIcon className="h-6 w-6 text-slate-400" />;
    case 3:
      return <TrophySolidIcon className="h-6 w-6 text-amber-600" />;
    default:
      return <span className="text-slate-500 font-mono">#{rank}</span>;
  }
};

export default function LeaderboardPage() {
  const [timeFrame, setTimeFrame] = useState<TimeFrame>('weekly');
  const { user, isAuthenticated } = useAuth();

  const { data: leaderboard, isLoading } = useQuery<LeaderboardEntry[]>({
    queryKey: ['leaderboard', timeFrame],
    queryFn: () => api.getLeaderboard({ timeframe: timeFrame }),
    staleTime: 60000, // 1 minute
  });

  // Find current user in leaderboard by username
  const currentUserRank = leaderboard?.findIndex((entry) => entry.username === user?.username);
  const userNotInTop = currentUserRank === -1 && isAuthenticated;

  return (
    <div className="min-h-screen bg-linear-to-br from-primary-50 via-white to-accent-50 dark:from-slate-900 dark:via-purple-900 dark:to-slate-900 py-12 px-4">
      <div className="max-w-3xl mx-auto">
        {/* Back Button */}
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 dark:text-slate-400 dark:hover:text-white transition-colors mb-8"
        >
          <ArrowLeftIcon className="h-5 w-5" />
          Back to polls
        </Link>

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <div className="inline-flex items-center justify-center gap-3 mb-4">
            <TrophyIcon className="h-10 w-10 text-yellow-500 dark:text-yellow-400" />
            <h1 className="text-4xl font-bold bg-linear-to-r from-yellow-500 to-amber-500 dark:from-yellow-400 dark:to-amber-400 bg-clip-text text-transparent">
              Leaderboard
            </h1>
          </div>
          <p className="text-gray-600 dark:text-slate-400">Top voters competing for glory</p>
        </motion.div>

        {/* Time Frame Tabs */}
        <div className="flex justify-center mb-8">
          <div className="inline-flex flex-wrap justify-center bg-gray-100 dark:bg-slate-800/50 rounded-xl p-1 border border-gray-200 dark:border-slate-700/50">
            {(Object.keys(timeFrameLabels) as TimeFrame[]).map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeFrame(tf)}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                  timeFrame === tf
                    ? 'bg-linear-to-r from-primary-600 to-accent-600 dark:from-purple-600 dark:to-cyan-600 text-white'
                    : 'text-gray-600 hover:text-gray-900 dark:text-slate-400 dark:hover:text-white'
                }`}
              >
                {timeFrameLabels[tf]}
              </button>
            ))}
          </div>
        </div>

        {/* Leaderboard Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white dark:bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-gray-200 dark:border-slate-700/50 overflow-hidden shadow-xl dark:shadow-2xl"
        >
          {isLoading ? (
            <div className="p-12 flex justify-center">
              <div className="animate-spin h-12 w-12 border-4 border-primary-500 dark:border-purple-500 border-t-transparent rounded-full"></div>
            </div>
          ) : !leaderboard || leaderboard.length === 0 ? (
            <div className="p-12 text-center">
              <ChartBarIcon className="h-16 w-16 text-gray-400 dark:text-slate-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">No data yet</h3>
              <p className="text-gray-600 dark:text-slate-400">Start voting to appear on the leaderboard!</p>
            </div>
          ) : (
            <>
              {/* Top 3 Podium */}
              <div className="p-6 pb-0">
                <div className="flex flex-col sm:flex-row justify-center items-center sm:items-end gap-4 sm:gap-4">
                  {/* 2nd Place */}
                  {leaderboard[1] && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.3 }}
                      className="text-center"
                    >
                      <div className="w-20 h-20 mx-auto mb-2 rounded-full bg-linear-to-br from-slate-200 to-slate-300 dark:from-slate-500/30 dark:to-slate-400/30 border-2 border-slate-300 dark:border-slate-500/50 flex items-center justify-center">
                        <UserCircleIcon className="h-12 w-12 text-slate-500 dark:text-slate-400" />
                      </div>
                      <p className="font-semibold text-gray-900 dark:text-white text-sm truncate max-w-25">
                        {leaderboard[1].display_name || leaderboard[1].username}
                      </p>
                      <p className="text-gray-600 dark:text-slate-400 text-sm">{leaderboard[1].points.toLocaleString()} pts</p>
                      <div className="h-16 w-20 bg-linear-to-t from-slate-200 to-transparent dark:from-slate-500/20 dark:to-transparent rounded-t-lg mt-2 flex items-end justify-center pb-2">
                        <TrophySolidIcon className="h-8 w-8 text-slate-400" />
                      </div>
                    </motion.div>
                  )}

                  {/* 1st Place */}
                  {leaderboard[0] && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.2 }}
                      className="text-center -mt-4"
                    >
                      <div className="relative">
                        <SparklesIcon className="absolute -top-2 -right-2 h-6 w-6 text-yellow-500 dark:text-yellow-400 animate-pulse" />
                        <div className="w-24 h-24 mx-auto mb-2 rounded-full bg-linear-to-br from-yellow-200 to-amber-300 dark:from-yellow-500/30 dark:to-amber-500/30 border-2 border-yellow-400 dark:border-yellow-500/50 flex items-center justify-center">
                          <UserCircleIcon className="h-14 w-14 text-yellow-600 dark:text-yellow-400" />
                        </div>
                      </div>
                      <p className="font-bold text-gray-900 dark:text-white truncate max-w-30">
                        {leaderboard[0].display_name || leaderboard[0].username}
                      </p>
                      <p className="text-yellow-600 dark:text-yellow-400 font-semibold">{leaderboard[0].points.toLocaleString()} pts</p>
                      <div className="h-24 w-24 bg-linear-to-t from-yellow-200 to-transparent dark:from-yellow-500/20 dark:to-transparent rounded-t-lg mt-2 flex items-end justify-center pb-2">
                        <TrophySolidIcon className="h-10 w-10 text-yellow-500 dark:text-yellow-400" />
                      </div>
                    </motion.div>
                  )}

                  {/* 3rd Place */}
                  {leaderboard[2] && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.4 }}
                      className="text-center"
                    >
                      <div className="w-20 h-20 mx-auto mb-2 rounded-full bg-linear-to-br from-amber-200 to-orange-300 dark:from-amber-600/30 dark:to-orange-600/30 border-2 border-amber-400 dark:border-amber-600/50 flex items-center justify-center">
                        <UserCircleIcon className="h-12 w-12 text-amber-700 dark:text-amber-600" />
                      </div>
                      <p className="font-semibold text-gray-900 dark:text-white text-sm truncate max-w-25">
                        {leaderboard[2].display_name || leaderboard[2].username}
                      </p>
                      <p className="text-gray-600 dark:text-slate-400 text-sm">{leaderboard[2].points.toLocaleString()} pts</p>
                      <div className="h-12 w-20 bg-linear-to-t from-amber-200 to-transparent dark:from-amber-600/20 dark:to-transparent rounded-t-lg mt-2 flex items-end justify-center pb-2">
                        <TrophySolidIcon className="h-6 w-6 text-amber-600" />
                      </div>
                    </motion.div>
                  )}
                </div>
              </div>

              {/* Full Rankings */}
              <div className="divide-y divide-gray-200 dark:divide-slate-700/50">
                <AnimatePresence>
                  {leaderboard.map((entry, index) => {
                    const isCurrentUser = entry.username === user?.username;
                    const rank = index + 1;

                    return (
                      <motion.div
                        key={entry.username}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.1 * Math.min(index, 10) }}
                        className={`flex items-center gap-4 p-4 ${
                          isCurrentUser ? 'bg-primary-50 dark:bg-purple-500/10' : ''
                        } hover:bg-gray-50 dark:hover:bg-slate-700/20 transition-colors`}
                      >
                        {/* Rank */}
                        <div className="w-10 flex justify-center">{getRankIcon(rank)}</div>

                        {/* User Info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <p
                              className={`font-semibold truncate ${
                                isCurrentUser ? 'text-primary-600 dark:text-purple-400' : 'text-gray-900 dark:text-white'
                              }`}
                            >
                              {entry.display_name || entry.username}
                              {isCurrentUser && ' (You)'}
                            </p>
                          </div>
                          <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-slate-400">
                            <span>Level {entry.level}: {entry.level_name}</span>
                          </div>
                        </div>

                        {/* Points */}
                        <div className="text-right">
                          <p className="font-bold text-gray-900 dark:text-white">{entry.points.toLocaleString()}</p>
                          <p className="text-xs text-gray-500 dark:text-slate-500">points</p>
                        </div>
                      </motion.div>
                    );
                  })}
                </AnimatePresence>
              </div>

              {/* Current User (if not in top list) */}
              {userNotInTop && (
                <div className="border-t border-gray-200 dark:border-slate-700/50 bg-primary-50 dark:bg-purple-500/10">
                  <div className="flex items-center gap-4 p-4">
                    <div className="w-10 flex justify-center">
                      <span className="text-gray-500 dark:text-slate-500 font-mono">#{currentUserRank ? currentUserRank + 1 : '?'}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-primary-600 dark:text-purple-400 truncate">{user?.display_name || user?.username} (You)</p>
                      <p className="text-sm text-gray-600 dark:text-slate-400">Keep voting to climb the ranks!</p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-gray-900 dark:text-white">{user?.points?.toLocaleString() || 0}</p>
                      <p className="text-xs text-gray-500 dark:text-slate-500">points</p>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </motion.div>

        {/* Earn More Points CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-8 bg-linear-to-br from-primary-50 to-accent-50 dark:from-slate-800/50 dark:to-purple-900/30 rounded-2xl border border-primary-200 dark:border-slate-700/50 p-6 relative overflow-hidden"
        >
          {/* Background decoration */}
          <div className="absolute top-0 right-0 w-32 h-32 bg-linear-to-br from-yellow-400/20 to-amber-500/20 rounded-full blur-2xl" />
          
          <div className="relative flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-linear-to-br from-yellow-400 to-amber-500 rounded-xl shadow-lg">
                <TrophyIcon className="h-8 w-8 text-white" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-1">
                  Want to Climb the Ranks?
                </h3>
                <p className="text-gray-600 dark:text-slate-400 max-w-md">
                  Earn points by voting on polls, maintaining streaks, completing your profile, and unlocking achievements. Every action counts!
                </p>
              </div>
            </div>
            
            <Link
              href="/achievements"
              className="inline-flex items-center gap-2 px-6 py-3 bg-linear-to-r from-primary-600 to-accent-600 dark:from-purple-600 dark:to-cyan-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl hover:from-primary-700 hover:to-accent-700 dark:hover:from-purple-700 dark:hover:to-cyan-700 transition-all whitespace-nowrap"
            >
              <SparklesIcon className="h-5 w-5" />
              View All Achievements
            </Link>
          </div>
          
          {/* Quick stats */}
          <div className="relative mt-6 pt-6 border-t border-primary-200/50 dark:border-slate-700/50 grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-primary-600 dark:text-cyan-400">+10</p>
              <p className="text-sm text-gray-600 dark:text-slate-400">per vote</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-amber-500 dark:text-yellow-400">+50</p>
              <p className="text-sm text-gray-600 dark:text-slate-400">streak bonus</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">+1000</p>
              <p className="text-sm text-gray-600 dark:text-slate-400">full profile</p>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
