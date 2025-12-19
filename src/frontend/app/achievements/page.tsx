'use client';

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { api, Achievement } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import {
  TrophyIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  CheckBadgeIcon,
  LockClosedIcon,
  ArrowLeftIcon,
  XMarkIcon,
  FireIcon,
  ChartBarIcon,
  UserCircleIcon,
  StarIcon,
  ShareIcon,
  HeartIcon,
  BoltIcon,
} from '@heroicons/react/24/outline';
import { CheckBadgeIcon as CheckBadgeSolidIcon, HeartIcon as HeartSolidIcon } from '@heroicons/react/24/solid';
import { ShareButtons } from '@/components/ui/social-share';

const tierColors: Record<string, { bg: string; border: string; text: string }> = {
  bronze: {
    bg: 'from-amber-600/20 to-amber-800/20',
    border: 'border-amber-600/40',
    text: 'text-amber-600 dark:text-amber-400',
  },
  silver: {
    bg: 'from-slate-300/20 to-slate-500/20',
    border: 'border-slate-400/40',
    text: 'text-slate-500 dark:text-slate-300',
  },
  gold: {
    bg: 'from-yellow-400/20 to-yellow-600/20',
    border: 'border-yellow-500/40',
    text: 'text-yellow-600 dark:text-yellow-400',
  },
  platinum: {
    bg: 'from-purple-400/20 to-cyan-400/20',
    border: 'border-purple-400/40',
    text: 'text-purple-500 dark:text-purple-400',
  },
};

const categoryInfo: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  voting: {
    label: 'Voting',
    icon: <CheckBadgeIcon className="h-5 w-5" />,
    color: 'text-green-500',
  },
  streak: {
    label: 'Streaks',
    icon: <FireIcon className="h-5 w-5" />,
    color: 'text-orange-500',
  },
  pulse: {
    label: 'Pulse Polls',
    icon: <HeartSolidIcon className="h-5 w-5" />,
    color: 'text-rose-500',
  },
  flash: {
    label: 'Flash Polls',
    icon: <BoltIcon className="h-5 w-5" />,
    color: 'text-amber-500',
  },
  profile: {
    label: 'Profile',
    icon: <UserCircleIcon className="h-5 w-5" />,
    color: 'text-blue-500',
  },
  leaderboard: {
    label: 'Leaderboard',
    icon: <TrophyIcon className="h-5 w-5" />,
    color: 'text-yellow-500',
  },
  sharing: {
    label: 'Sharing',
    icon: <ShareIcon className="h-5 w-5" />,
    color: 'text-pink-500',
  },
  support: {
    label: 'Support',
    icon: <HeartIcon className="h-5 w-5" />,
    color: 'text-red-500',
  },
};

const tierOrder = ['bronze', 'silver', 'gold', 'platinum'];

export default function AchievementsPage() {
  const { isAuthenticated } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedTier, setSelectedTier] = useState<string | null>(null);
  const [showUnlockedOnly, setShowUnlockedOnly] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  // Fetch achievements based on auth status
  const { data: achievements, isLoading } = useQuery<Achievement[]>({
    queryKey: ['all-achievements', isAuthenticated, selectedCategory, selectedTier, searchQuery, showUnlockedOnly],
    queryFn: () => {
      if (isAuthenticated) {
        return api.getUserAchievements({
          category: selectedCategory || undefined,
          tier: selectedTier || undefined,
          search: searchQuery || undefined,
          unlocked_only: showUnlockedOnly,
        });
      } else {
        return api.getAllAchievements({
          category: selectedCategory || undefined,
          tier: selectedTier || undefined,
          search: searchQuery || undefined,
        });
      }
    },
  });

  // Calculate stats
  const stats = useMemo(() => {
    if (!achievements) return { total: 0, unlocked: 0, totalPoints: 0, earnedPoints: 0 };
    
    const total = achievements.length;
    const unlocked = achievements.filter(a => a.is_unlocked).length;
    const totalPoints = achievements.reduce((sum, a) => sum + a.points_reward, 0);
    const earnedPoints = achievements
      .filter(a => a.is_unlocked)
      .reduce((sum, a) => sum + (a.times_earned || 1) * a.points_reward, 0);
    
    return { total, unlocked, totalPoints, earnedPoints };
  }, [achievements]);

  // Group achievements by category
  const groupedAchievements = useMemo(() => {
    if (!achievements) return {};
    
    const grouped: Record<string, Achievement[]> = {};
    for (const achievement of achievements) {
      const category = achievement.category || 'other';
      if (!grouped[category]) grouped[category] = [];
      grouped[category].push(achievement);
    }
    
    // Sort each category by tier and then sort_order
    for (const category of Object.keys(grouped)) {
      grouped[category].sort((a, b) => {
        const tierA = tierOrder.indexOf(a.tier || 'bronze');
        const tierB = tierOrder.indexOf(b.tier || 'bronze');
        if (tierA !== tierB) return tierA - tierB;
        return 0;
      });
    }
    
    return grouped;
  }, [achievements]);

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedCategory(null);
    setSelectedTier(null);
    setShowUnlockedOnly(false);
  };

  const hasActiveFilters = searchQuery || selectedCategory || selectedTier || showUnlockedOnly;

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white dark:from-slate-900 dark:to-slate-800">
      {/* Header */}
      <div className="bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-gray-200 dark:border-slate-700 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4 mb-4">
            <Link
              href="/"
              className="p-2 rounded-lg bg-gray-100 dark:bg-slate-800 hover:bg-gray-200 dark:hover:bg-slate-700 transition-colors"
            >
              <ArrowLeftIcon className="h-5 w-5 text-gray-600 dark:text-slate-400" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Achievements</h1>
              <p className="text-sm text-gray-600 dark:text-slate-400">
                {isAuthenticated
                  ? `${stats.unlocked} of ${stats.total} unlocked • ${stats.earnedPoints.toLocaleString()} points earned`
                  : `${stats.total} achievements • ${stats.totalPoints.toLocaleString()} total points available`}
              </p>
            </div>
          </div>

          {/* Search and Filter Bar */}
          <div className="flex flex-col sm:flex-row gap-3">
            {/* Search Input */}
            <div className="relative flex-1">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search achievements..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-gray-100 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50 dark:focus:ring-cyan-500/50"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-white"
                >
                  <XMarkIcon className="h-5 w-5" />
                </button>
              )}
            </div>

            {/* Filter Toggle Button */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border transition-colors ${
                hasActiveFilters
                  ? 'bg-primary-100 dark:bg-cyan-500/20 border-primary-300 dark:border-cyan-500/40 text-primary-700 dark:text-cyan-400'
                  : 'bg-gray-100 dark:bg-slate-800 border-gray-200 dark:border-slate-700 text-gray-700 dark:text-slate-300 hover:bg-gray-200 dark:hover:bg-slate-700'
              }`}
            >
              <FunnelIcon className="h-5 w-5" />
              <span className="hidden sm:inline">Filters</span>
              {hasActiveFilters && (
                <span className="bg-primary-500 dark:bg-cyan-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                  {[selectedCategory, selectedTier, showUnlockedOnly].filter(Boolean).length + (searchQuery ? 1 : 0)}
                </span>
              )}
            </button>
          </div>

          {/* Expanded Filters */}
          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="pt-4 space-y-4">
                  {/* Category Filter */}
                  <div>
                    <label className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-2 block">
                      Category
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(categoryInfo).map(([key, { label, icon, color }]) => (
                        <button
                          key={key}
                          onClick={() => setSelectedCategory(selectedCategory === key ? null : key)}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                            selectedCategory === key
                              ? 'bg-primary-500 dark:bg-cyan-500 text-white'
                              : 'bg-gray-100 dark:bg-slate-800 text-gray-700 dark:text-slate-300 hover:bg-gray-200 dark:hover:bg-slate-700'
                          }`}
                        >
                          <span className={selectedCategory === key ? 'text-white' : color}>{icon}</span>
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Tier Filter */}
                  <div>
                    <label className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-2 block">
                      Tier
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {tierOrder.map((tier) => (
                        <button
                          key={tier}
                          onClick={() => setSelectedTier(selectedTier === tier ? null : tier)}
                          className={`px-3 py-1.5 rounded-full text-sm font-medium capitalize transition-colors ${
                            selectedTier === tier
                              ? 'bg-primary-500 dark:bg-cyan-500 text-white'
                              : `bg-gradient-to-r ${tierColors[tier].bg} ${tierColors[tier].border} border ${tierColors[tier].text}`
                          }`}
                        >
                          {tier}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Unlocked Only Toggle (only for authenticated users) */}
                  {isAuthenticated && (
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => setShowUnlockedOnly(!showUnlockedOnly)}
                        className={`relative w-11 h-6 rounded-full transition-colors ${
                          showUnlockedOnly ? 'bg-primary-500 dark:bg-cyan-500' : 'bg-gray-300 dark:bg-slate-600'
                        }`}
                      >
                        <span
                          className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                            showUnlockedOnly ? 'translate-x-5' : ''
                          }`}
                        />
                      </button>
                      <span className="text-sm text-gray-700 dark:text-slate-300">
                        Show unlocked only
                      </span>
                    </div>
                  )}

                  {/* Clear Filters */}
                  {hasActiveFilters && (
                    <button
                      onClick={clearFilters}
                      className="text-sm text-primary-600 dark:text-cyan-400 hover:text-primary-700 dark:hover:text-cyan-300"
                    >
                      Clear all filters
                    </button>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-4 py-6">
        {/* Login Prompt for non-authenticated users */}
        {!isAuthenticated && (
          <div className="mb-6 p-4 bg-primary-50 dark:bg-cyan-500/10 border border-primary-200 dark:border-cyan-500/30 rounded-xl">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary-100 dark:bg-cyan-500/20 rounded-lg">
                <StarIcon className="h-5 w-5 text-primary-600 dark:text-cyan-400" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-primary-900 dark:text-cyan-100">
                  Sign in to track your progress
                </p>
                <p className="text-xs text-primary-700 dark:text-cyan-300">
                  See which achievements you&apos;ve earned and track your progress toward new ones.
                </p>
              </div>
              <Link
                href="/login"
                className="px-4 py-2 bg-primary-500 dark:bg-cyan-500 text-white text-sm font-medium rounded-lg hover:bg-primary-600 dark:hover:bg-cyan-600 transition-colors"
              >
                Sign In
              </Link>
            </div>
          </div>
        )}

        {/* Community Achievements Banner */}
        <div className="mb-6">
          <Link href="/community">
            <motion.div 
              whileHover={{ scale: 1.01 }}
              className="p-4 bg-gradient-to-r from-purple-600 to-indigo-600 rounded-xl text-white cursor-pointer"
            >
              <div className="flex items-center gap-4">
                <div className="p-3 bg-white/20 rounded-xl">
                  <span className="text-2xl">🎯</span>
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-bold">Community Achievements</h3>
                  <p className="text-purple-100 text-sm">
                    Join the community to unlock special badges and bonus points together!
                  </p>
                </div>
                <div className="hidden sm:flex items-center gap-2 px-4 py-2 bg-white/20 rounded-lg">
                  <span className="text-sm font-medium">View All</span>
                  <ArrowLeftIcon className="h-4 w-4 rotate-180" />
                </div>
              </div>
            </motion.div>
          </Link>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse">
                <div className="h-6 bg-gray-200 dark:bg-slate-700 rounded w-32 mb-4" />
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {[1, 2, 3].map((j) => (
                    <div key={j} className="h-32 bg-gray-200 dark:bg-slate-700 rounded-xl" />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Achievements Grid */}
        {!isLoading && achievements && (
          <div className="space-y-8">
            {Object.entries(groupedAchievements).map(([category, categoryAchievements]) => {
              const info = categoryInfo[category] || {
                label: category,
                icon: <StarIcon className="h-5 w-5" />,
                color: 'text-gray-500',
              };

              return (
                <div key={category}>
                  <div className="flex items-center gap-2 mb-4">
                    <span className={info.color}>{info.icon}</span>
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                      {info.label}
                    </h2>
                    <span className="text-sm text-gray-500 dark:text-slate-500">
                      ({categoryAchievements.length})
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {categoryAchievements.map((achievement) => (
                      <AchievementCard
                        key={achievement.id}
                        achievement={achievement}
                        isAuthenticated={isAuthenticated}
                      />
                    ))}
                  </div>
                </div>
              );
            })}

            {/* Empty State */}
            {Object.keys(groupedAchievements).length === 0 && (
              <div className="text-center py-12">
                <TrophyIcon className="h-16 w-16 text-gray-300 dark:text-slate-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  No achievements found
                </h3>
                <p className="text-gray-600 dark:text-slate-400 mb-4">
                  Try adjusting your search or filters.
                </p>
                {hasActiveFilters && (
                  <button
                    onClick={clearFilters}
                    className="text-primary-600 dark:text-cyan-400 hover:text-primary-700 dark:hover:text-cyan-300 font-medium"
                  >
                    Clear all filters
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function AchievementCard({
  achievement,
  isAuthenticated,
}: {
  achievement: Achievement;
  isAuthenticated: boolean;
}) {
  const tier = achievement.tier || 'bronze';
  const colors = tierColors[tier];
  const isUnlocked = achievement.is_unlocked;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`relative p-4 rounded-xl border bg-gradient-to-br ${colors.bg} ${colors.border} ${
        !isUnlocked && isAuthenticated ? 'opacity-60' : ''
      }`}
    >
      {/* Unlocked Badge */}
      {isAuthenticated && isUnlocked && (
        <div className="absolute -top-2 -right-2">
          <div className="bg-green-500 rounded-full p-1">
            <CheckBadgeSolidIcon className="h-4 w-4 text-white" />
          </div>
        </div>
      )}

      {/* Lock Icon for locked achievements */}
      {isAuthenticated && !isUnlocked && (
        <div className="absolute -top-2 -right-2">
          <div className="bg-gray-400 dark:bg-slate-600 rounded-full p-1">
            <LockClosedIcon className="h-4 w-4 text-white" />
          </div>
        </div>
      )}

      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="text-3xl flex-shrink-0">{achievement.icon}</div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 dark:text-white truncate">
            {achievement.name}
          </h3>
          <p className="text-sm text-gray-600 dark:text-slate-400 line-clamp-2 mb-2">
            {achievement.description}
          </p>

          {/* Points and Tier */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-primary-600 dark:text-cyan-400">
              +{achievement.points_reward} pts
            </span>
            <span className={`text-xs font-medium capitalize ${colors.text}`}>
              {tier}
            </span>
          </div>

          {/* Progress Bar (for authenticated users with locked achievements) */}
          {isAuthenticated && !isUnlocked && achievement.target > 1 && (
            <div className="mt-2">
              <div className="flex items-center justify-between text-xs text-gray-500 dark:text-slate-500 mb-1">
                <span>Progress</span>
                <span>
                  {achievement.progress} / {achievement.target}
                </span>
              </div>
              <div className="h-1.5 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary-500 dark:bg-cyan-500 rounded-full transition-all"
                  style={{ width: `${Math.min(100, (achievement.progress / achievement.target) * 100)}%` }}
                />
              </div>
            </div>
          )}

          {/* Times Earned (for repeatable achievements) */}
          {isAuthenticated && isUnlocked && achievement.is_repeatable && (achievement.times_earned || 0) > 1 && (
            <div className="mt-2 text-xs text-gray-500 dark:text-slate-500">
              Earned {achievement.times_earned} times
            </div>
          )}

          {/* Unlocked Date */}
          {isAuthenticated && isUnlocked && achievement.unlocked_at && (
            <div className="mt-2 flex items-center justify-between">
              <span className="text-xs text-gray-500 dark:text-slate-500">
                Earned {new Date(achievement.unlocked_at).toLocaleDateString()}
              </span>
              <ShareButtons
                content={{
                  title: `I earned the "${achievement.name}" achievement on TruePulse!`,
                  text: `🏆 I just unlocked "${achievement.name}" - ${achievement.description}. Join TruePulse and start earning achievements!`,
                  url: typeof window !== 'undefined' ? `${window.location.origin}/achievements` : '/achievements',
                  hashtags: ['TruePulse', 'Achievement'],
                }}
              />
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
