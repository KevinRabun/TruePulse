'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { api, UserProfile, Achievement } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import {
  UserCircleIcon,
  TrophyIcon,
  FireIcon,
  ChartBarIcon,
  CogIcon,
  ArrowLeftIcon,
  CheckBadgeIcon,
  LockClosedIcon,
  PencilIcon,
  CameraIcon,
  ShieldCheckIcon,
  EnvelopeIcon,
} from '@heroicons/react/24/outline';
import { CheckBadgeIcon as CheckBadgeSolidIcon } from '@heroicons/react/24/solid';
import { DemographicsForm } from '@/components/profile/demographics-form';
import { ThemeSettings } from '@/components/profile/theme-settings';
import { PollNotifications } from '@/components/profile/poll-notifications';
import { VerificationStatus } from '@/components/profile/verification-status';
import { PasskeyManagement } from '@/components/auth';

const achievementIcons: Record<string, React.ReactNode> = {
  first_vote: <CheckBadgeSolidIcon className="h-8 w-8 text-green-400" />,
  streak_3: <FireIcon className="h-8 w-8 text-orange-300" />,
  streak_7: <FireIcon className="h-8 w-8 text-orange-400" />,
  streak_14: <FireIcon className="h-8 w-8 text-orange-500" />,
  streak_30: <FireIcon className="h-8 w-8 text-red-500" />,
  streak_90: <FireIcon className="h-8 w-8 text-red-600" />,
  streak_365: <FireIcon className="h-8 w-8 text-red-700" />,
  votes_10: <ChartBarIcon className="h-8 w-8 text-blue-300" />,
  votes_50: <ChartBarIcon className="h-8 w-8 text-blue-400" />,
  votes_100: <ChartBarIcon className="h-8 w-8 text-blue-500" />,
  votes_500: <ChartBarIcon className="h-8 w-8 text-purple-400" />,
  early_adopter: <TrophyIcon className="h-8 w-8 text-yellow-400" />,
  daily_rank_1: <TrophyIcon className="h-8 w-8 text-yellow-400" />,
  daily_rank_2: <TrophyIcon className="h-8 w-8 text-slate-300" />,
  daily_rank_3: <TrophyIcon className="h-8 w-8 text-amber-600" />,
  monthly_rank_1: <TrophyIcon className="h-8 w-8 text-yellow-500" />,
  monthly_rank_2: <TrophyIcon className="h-8 w-8 text-slate-400" />,
  monthly_rank_3: <TrophyIcon className="h-8 w-8 text-amber-700" />,
  yearly_rank_1: <TrophyIcon className="h-8 w-8 text-yellow-600" />,
  yearly_rank_2: <TrophyIcon className="h-8 w-8 text-slate-500" />,
  yearly_rank_3: <TrophyIcon className="h-8 w-8 text-amber-800" />,
  // Verification achievements
  email_verified: <EnvelopeIcon className="h-8 w-8 text-blue-400" />,
  passkey_verified: <ShieldCheckIcon className="h-8 w-8 text-green-400" />,
  fully_verified: <ShieldCheckIcon className="h-8 w-8 text-green-500" />,
};

const tierColors: Record<string, string> = {
  bronze: 'from-amber-600/20 to-amber-800/20 border-amber-600/40',
  silver: 'from-slate-300/20 to-slate-500/20 border-slate-400/40',
  gold: 'from-yellow-400/20 to-yellow-600/20 border-yellow-500/40',
  platinum: 'from-purple-400/20 to-cyan-400/20 border-purple-400/40',
};

const categoryLabels: Record<string, string> = {
  voting: '🗳️ Voting',
  streak: '🔥 Streaks',
  profile: '👤 Profile',
  verification: '✅ Verification',
  leaderboard: '🏆 Leaderboard',
};

export default function ProfilePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, isAuthenticated, logout } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [displayName, setDisplayName] = useState(user?.display_name || '');
  const [activeTab, setActiveTab] = useState<'overview' | 'achievements' | 'history' | 'settings'>('overview');

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  const { data: profile, isLoading } = useQuery<UserProfile>({
    queryKey: ['profile'],
    queryFn: () => api.getProfile(),
    enabled: isAuthenticated,
  });

  const { data: achievements } = useQuery<Achievement[]>({
    queryKey: ['achievements'],
    queryFn: () => api.getAchievements(),
    enabled: isAuthenticated,
  });

  const updateProfileMutation = useMutation({
    mutationFn: (data: { display_name: string }) => api.updateProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] });
      setIsEditing(false);
    },
  });

  const handleSave = () => {
    if (displayName.trim().length >= 2) {
      updateProfileMutation.mutate({ display_name: displayName.trim() });
    }
  };

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  // Show loading or redirect state
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-linear-to-br from-primary-50 via-white to-accent-50 dark:from-slate-900 dark:via-purple-900 dark:to-slate-900 flex items-center justify-center">
        <div className="animate-spin h-12 w-12 border-4 border-primary-500 dark:border-purple-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (isLoading || !profile) {
    return (
      <div className="min-h-screen bg-linear-to-br from-primary-50 via-white to-accent-50 dark:from-slate-900 dark:via-purple-900 dark:to-slate-900 flex items-center justify-center">
        <div className="animate-spin h-12 w-12 border-4 border-primary-500 dark:border-purple-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-linear-to-br from-primary-50 via-white to-accent-50 dark:from-slate-900 dark:via-purple-900 dark:to-slate-900 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Back Button */}
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 dark:text-slate-400 dark:hover:text-white transition-colors mb-8"
        >
          <ArrowLeftIcon className="h-5 w-5" />
          Back to polls
        </Link>

        {/* Profile Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white dark:bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-gray-200 dark:border-slate-700/50 overflow-hidden shadow-xl dark:shadow-2xl mb-8"
        >
          {/* Cover */}
          <div className="h-32 bg-linear-to-r from-primary-600 to-accent-600 dark:from-purple-600 dark:to-cyan-600 relative">
            <button className="absolute bottom-4 right-4 p-2 bg-black/20 rounded-lg text-white/70 hover:text-white hover:bg-black/40 transition-colors">
              <CameraIcon className="h-5 w-5" />
            </button>
          </div>

          {/* Avatar & Info */}
          <div className="px-6 pb-6">
            <div className="flex flex-col md:flex-row md:items-end gap-4 -mt-12">
              <div className="relative">
                <div className="w-24 h-24 rounded-full bg-white dark:bg-slate-800 border-4 border-white dark:border-slate-800 flex items-center justify-center">
                  <UserCircleIcon className="h-20 w-20 text-gray-400 dark:text-slate-400" />
                </div>
                <button className="absolute bottom-0 right-0 p-1.5 bg-primary-600 dark:bg-purple-600 rounded-full text-white hover:bg-primary-500 dark:hover:bg-purple-500 transition-colors">
                  <CameraIcon className="h-4 w-4" />
                </button>
              </div>

              <div className="flex-1">
                {isEditing ? (
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      className="text-2xl font-bold bg-gray-100 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg px-3 py-1 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-primary-500 dark:focus:ring-purple-500"
                      maxLength={50}
                    />
                    <button
                      onClick={handleSave}
                      disabled={updateProfileMutation.isPending}
                      className="px-4 py-1.5 bg-green-600 text-white rounded-lg hover:bg-green-500 transition-colors"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => {
                        setIsEditing(false);
                        setDisplayName(profile.display_name);
                      }}
                      className="px-4 py-1.5 bg-gray-200 dark:bg-slate-700 text-gray-700 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-slate-600 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{profile.display_name}</h1>
                    <button
                      onClick={() => setIsEditing(true)}
                      className="p-1 text-gray-400 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white transition-colors"
                    >
                      <PencilIcon className="h-4 w-4" />
                    </button>
                  </div>
                )}
                <p className="text-gray-600 dark:text-slate-400 text-sm mt-1">Member since {new Date(profile.created_at).toLocaleDateString()}</p>
              </div>

              <div className="flex gap-2">
                <button className="p-2 text-gray-400 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-slate-700/50 rounded-lg transition-colors">
                  <CogIcon className="h-6 w-6" />
                </button>
                <button
                  onClick={handleLogout}
                  className="px-4 py-2 text-red-500 dark:text-red-400 hover:text-white hover:bg-red-500/20 rounded-lg transition-colors"
                >
                  Sign out
                </button>
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
              {[
                { label: 'Points', value: profile.points.toLocaleString(), icon: <TrophyIcon className="h-5 w-5 text-yellow-500 dark:text-yellow-400" /> },
                { label: 'Total Votes', value: profile.total_votes.toLocaleString(), icon: <ChartBarIcon className="h-5 w-5 text-primary-500 dark:text-cyan-400" /> },
                { label: 'Current Streak', value: `${profile.current_streak} days`, icon: <FireIcon className="h-5 w-5 text-orange-500 dark:text-orange-400" /> },
                { label: 'Achievements', value: profile.achievements_count.toString(), icon: <CheckBadgeIcon className="h-5 w-5 text-accent-500 dark:text-purple-400" /> },
              ].map((stat) => (
                <div key={stat.label} className="bg-gray-100 dark:bg-slate-900/50 rounded-xl p-4 text-center">
                  <div className="flex justify-center mb-2">{stat.icon}</div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{stat.value}</p>
                  <p className="text-sm text-gray-600 dark:text-slate-400">{stat.label}</p>
                </div>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Tabs */}
        <div className="flex overflow-x-auto scrollbar-hide border-b border-gray-200 dark:border-slate-700/50 mb-6">
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'achievements', label: 'Achievements' },
            { id: 'history', label: 'Voting History' },
            { id: 'settings', label: 'Settings', icon: <CogIcon className="h-4 w-4" /> },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`px-6 py-3 font-medium transition-colors relative flex items-center gap-2 ${
                activeTab === tab.id ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              {'icon' in tab && tab.icon}
              {tab.label}
              {activeTab === tab.id && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-linear-to-r from-primary-600 to-accent-600 dark:from-purple-600 dark:to-cyan-600"
                />
              )}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <AnimatePresence mode="wait">
          {activeTab === 'overview' && (
            <motion.div
              key="overview"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="grid md:grid-cols-2 gap-6"
            >
              {/* Recent Activity */}
              <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-gray-200 dark:border-slate-700/50 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Recent Activity</h3>
                <div className="space-y-4">
                  {profile.recent_votes?.slice(0, 5).map((vote, index) => (
                    <div key={index} className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-primary-500 dark:bg-cyan-400"></div>
                      <div className="flex-1">
                        <p className="text-gray-900 dark:text-white text-sm">{vote.poll_question}</p>
                        <p className="text-gray-500 dark:text-slate-500 text-xs">{new Date(vote.voted_at).toLocaleDateString()}</p>
                      </div>
                    </div>
                  )) || (
                    <p className="text-gray-600 dark:text-slate-400 text-sm">No recent activity</p>
                  )}
                </div>
              </div>

              {/* Streak Calendar */}
              <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-gray-200 dark:border-slate-700/50 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  <FireIcon className="h-5 w-5 text-orange-500 dark:text-orange-400" />
                  Voting Streak
                </h3>
                <div className="text-center py-8">
                  <p className="text-6xl font-bold text-orange-500 dark:text-orange-400">{profile.current_streak}</p>
                  <p className="text-gray-600 dark:text-slate-400 mt-2">day streak</p>
                  {profile.longest_streak && (
                    <p className="text-sm text-gray-500 dark:text-slate-500 mt-4">
                      Longest streak: {profile.longest_streak} days
                    </p>
                  )}
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'achievements' && (
            <motion.div
              key="achievements"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="bg-white dark:bg-slate-800/50 rounded-xl border border-gray-200 dark:border-slate-700/50 p-6"
            >
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Your Achievements</h3>
              
              {/* Group achievements by category */}
              {['voting', 'streak', 'profile', 'leaderboard'].map((category) => {
                const categoryAchievements = achievements?.filter(a => a.category === category) || [];
                if (categoryAchievements.length === 0) return null;
                
                return (
                  <div key={category} className="mb-8 last:mb-0">
                    <h4 className="text-md font-medium text-gray-700 dark:text-slate-300 mb-4">
                      {categoryLabels[category] || category}
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {categoryAchievements.map((achievement) => {
                        const isUnlocked = achievement.is_unlocked || achievement.unlocked;
                        const tierStyle = achievement.tier && tierColors[achievement.tier] ? tierColors[achievement.tier] : '';
                        
                        return (
                          <div
                            key={achievement.id}
                            className={`p-4 rounded-xl border text-center transition-all ${
                              isUnlocked
                                ? `bg-linear-to-br ${tierStyle || 'from-primary-100 to-accent-100 border-primary-300 dark:from-purple-500/10 dark:to-cyan-500/10 dark:border-purple-500/30'}`
                                : 'bg-gray-100 dark:bg-slate-900/30 border-gray-200 dark:border-slate-700/30 opacity-50'
                            }`}
                          >
                            <div className="flex justify-center mb-3">
                              {isUnlocked ? (
                                achievement.icon ? (
                                  <span className="text-3xl">{achievement.icon}</span>
                                ) : (
                                  achievementIcons[achievement.id] || <CheckBadgeSolidIcon className="h-8 w-8 text-accent-500 dark:text-purple-400" />
                                )
                              ) : (
                                <LockClosedIcon className="h-8 w-8 text-gray-400 dark:text-slate-600" />
                              )}
                            </div>
                            <h4 className={`font-semibold ${isUnlocked ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-slate-500'}`}>
                              {achievement.name}
                            </h4>
                            <p className="text-sm text-gray-600 dark:text-slate-400 mt-1">{achievement.description}</p>
                            
                            {/* Points reward */}
                            {achievement.points_reward > 0 && (
                              <p className={`text-xs mt-2 ${isUnlocked ? 'text-primary-600 dark:text-cyan-400' : 'text-gray-500 dark:text-slate-500'}`}>
                                +{achievement.points_reward} points
                              </p>
                            )}
                            
                            {/* Progress bar for locked achievements */}
                            {!isUnlocked && achievement.target > 1 && (
                              <div className="mt-3">
                                <div className="w-full bg-gray-200 dark:bg-slate-700 rounded-full h-1.5">
                                  <div
                                    className="bg-primary-500 dark:bg-cyan-500 h-1.5 rounded-full transition-all"
                                    style={{ width: `${Math.min(100, (achievement.progress / achievement.target) * 100)}%` }}
                                  />
                                </div>
                                <p className="text-xs text-gray-500 dark:text-slate-500 mt-1">
                                  {achievement.progress} / {achievement.target}
                                </p>
                              </div>
                            )}
                            
                            {/* Earned date(s) */}
                            {isUnlocked && (
                              <>
                                {achievement.is_repeatable && achievement.times_earned && achievement.times_earned > 1 ? (
                                  <p className="text-xs text-gray-500 dark:text-slate-500 mt-2">
                                    Earned {achievement.times_earned} times
                                  </p>
                                ) : achievement.unlocked_at ? (
                                  <p className="text-xs text-gray-500 dark:text-slate-500 mt-2">
                                    Unlocked {new Date(achievement.unlocked_at).toLocaleDateString()}
                                  </p>
                                ) : null}
                              </>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
              
              {(!achievements || achievements.length === 0) && (
                <p className="col-span-full text-center text-gray-600 dark:text-slate-400">
                  Complete actions to earn achievements!
                </p>
              )}
            </motion.div>
          )}

          {activeTab === 'history' && (
            <motion.div
              key="history"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="bg-white dark:bg-slate-800/50 rounded-xl border border-gray-200 dark:border-slate-700/50 p-6"
            >
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Voting History</h3>
                <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
                  <LockClosedIcon className="h-4 w-4" />
                  <span>Your votes are private</span>
                </div>
              </div>
              <div className="space-y-3">
                {profile.recent_votes?.map((vote, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-4 p-4 bg-gray-50 dark:bg-slate-900/30 rounded-xl hover:bg-gray-100 dark:hover:bg-slate-900/50 transition-colors"
                  >
                    <div className="flex-1">
                      <Link href={`/poll?id=${vote.poll_id}`} className="text-gray-900 dark:text-white hover:text-primary-600 dark:hover:text-cyan-400 transition-colors">
                        {vote.poll_question}
                      </Link>
                      <p className="text-sm text-gray-500 dark:text-slate-500">
                        {new Date(vote.voted_at).toLocaleDateString()} at {new Date(vote.voted_at).toLocaleTimeString()}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-500 dark:text-slate-400">+10 pts</p>
                    </div>
                  </div>
                )) || (
                  <p className="text-center text-gray-600 dark:text-slate-400 py-8">
                    No voting history yet. Start participating in polls!
                  </p>
                )}
              </div>
            </motion.div>
          )}

          {activeTab === 'settings' && (
            <motion.div
              key="settings"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-6"
            >
              {/* Verification Status - Show first for prominence */}
              <VerificationStatus
                emailVerified={profile.email_verified}
                email={profile.email}
                onResendEmail={async () => {
                  await api.sendVerificationEmail(profile.email);
                }}
              />

              {/* Theme Settings */}
              <ThemeSettings
                onUpdate={() => queryClient.invalidateQueries({ queryKey: ['profile'] })}
              />

              {/* Demographics */}
              <DemographicsForm
                onUpdate={() => queryClient.invalidateQueries({ queryKey: ['profile'] })}
              />

              {/* Passkey Management */}
              <PasskeyManagement
                onUpdate={() => queryClient.invalidateQueries({ queryKey: ['profile'] })}
              />

              {/* Poll Notifications */}
              <PollNotifications
                onUpdate={() => queryClient.invalidateQueries({ queryKey: ['profile'] })}
              />

              {/* Account Security */}
              <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-gray-200 dark:border-slate-700/50 p-6">
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-2 bg-red-100 dark:bg-red-500/20 rounded-lg">
                    <LockClosedIcon className="h-6 w-6 text-red-500 dark:text-red-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Account Security</h3>
                    <p className="text-sm text-gray-600 dark:text-slate-400">Manage your account settings</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <button
                    onClick={handleLogout}
                    className="w-full py-3 text-red-500 dark:text-red-400 hover:text-white hover:bg-red-500/20 rounded-lg border border-red-300 dark:border-red-500/30 transition-colors"
                  >
                    Sign out of your account
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
