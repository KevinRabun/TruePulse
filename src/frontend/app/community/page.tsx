'use client';

import { motion } from 'framer-motion';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import Link from 'next/link';
import { CommunityAchievements } from '@/components/home/community-achievements';

export default function CommunityPage() {
  return (
    <div className="min-h-screen bg-linear-to-br from-slate-50 via-blue-50/30 to-indigo-50/50 dark:from-slate-900 dark:via-slate-900 dark:to-slate-800">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border-b border-gray-200/50 dark:border-slate-700/50">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="p-2 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
            >
              <ArrowLeftIcon className="h-5 w-5 text-gray-600 dark:text-slate-400" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                Community Achievements
              </h1>
              <p className="text-sm text-gray-600 dark:text-slate-400">
                Join forces with the community to unlock special rewards
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 py-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {/* Intro Section */}
          <div className="mb-8 p-6 bg-linear-to-r from-purple-600 to-indigo-600 rounded-2xl text-white">
            <h2 className="text-2xl font-bold mb-2">🎯 Unite for Greater Rewards</h2>
            <p className="text-purple-100 mb-4">
              Community achievements are special challenges where everyone works together toward a common goal. 
              When the community reaches the target, all participants earn exclusive badges and bonus points!
            </p>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div className="bg-white/10 rounded-xl p-3">
                <div className="text-2xl font-bold">🏆</div>
                <div className="text-sm text-purple-100">Exclusive Badges</div>
              </div>
              <div className="bg-white/10 rounded-xl p-3">
                <div className="text-2xl font-bold">⚡</div>
                <div className="text-sm text-purple-100">Bonus Points</div>
              </div>
              <div className="bg-white/10 rounded-xl p-3">
                <div className="text-2xl font-bold">🤝</div>
                <div className="text-sm text-purple-100">Team Spirit</div>
              </div>
            </div>
          </div>

          {/* Community Achievements Component */}
          <CommunityAchievements />
        </motion.div>
      </div>
    </div>
  );
}
