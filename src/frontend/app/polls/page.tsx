'use client';

import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { PollCard } from '@/components/polls/poll-card';
import { api, type Poll, type PollType } from '@/lib/api';
import { NativeAd } from '@/components/ads';
import {
  FunnelIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  HeartIcon,
  BoltIcon,
} from '@heroicons/react/24/outline';

// Categories for filtering
const categories = [
  'All',
  'Technology',
  'Politics',
  'Environment',
  'Economy',
  'Health',
  'Sports',
  'Entertainment',
  'Workplace',
  'Science',
];

interface DisplayPoll {
  id: string;
  question: string;
  choices: { id: string; text: string; votePercentage: number }[];
  totalVotes: number;
  category: string;
  sourceEvent?: string;
  expiresAt: Date;
  pollType?: PollType;
  isClosed?: boolean;
}

function transformPoll(poll: Poll): DisplayPoll {
  const totalVotes = poll.total_votes || 0;
  const expiresAt = new Date(poll.expires_at);
  return {
    id: poll.id,
    question: poll.question,
    choices: poll.choices.map((c) => ({
      id: c.id,
      text: c.text,
      votePercentage: totalVotes > 0 && c.vote_count
        ? Math.round((c.vote_count / totalVotes) * 100)
        : 0,
    })),
    totalVotes,
    category: poll.category,
    sourceEvent: poll.source_event,
    expiresAt,
    pollType: poll.poll_type,
    isClosed: expiresAt < new Date() || poll.status === 'closed',
  };
}

export default function PollsPage() {
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedPollType, setSelectedPollType] = useState<'all' | 'pulse' | 'flash' | 'standard'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [polls, setPolls] = useState<DisplayPoll[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchPolls = async () => {
      try {
        // Fetch previous/closed polls from history endpoints
        const [pulseHistory, flashHistory] = await Promise.all([
          api.getPulsePollHistory(1, 20),
          api.getFlashPollHistory(1, 20),
        ]);
        
        const allPolls: DisplayPoll[] = [];
        const now = new Date();
        
        // Add closed Pulse polls
        pulseHistory.polls.forEach(poll => {
          const transformed = transformPoll(poll);
          // Only include closed polls
          if (transformed.expiresAt < now || poll.status === 'closed') {
            allPolls.push(transformed);
          }
        });
        
        // Add closed Flash polls
        flashHistory.polls.forEach(poll => {
          const transformed = transformPoll(poll);
          // Only include closed polls
          if (transformed.expiresAt < now || poll.status === 'closed') {
            allPolls.push(transformed);
          }
        });
        
        // Sort by expiry date (most recent first)
        allPolls.sort((a, b) => b.expiresAt.getTime() - a.expiresAt.getTime());
        
        setPolls(allPolls);
      } catch (error) {
        console.error('Failed to fetch polls:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchPolls();
  }, []);

  // Filter polls based on category, poll type, and search
  const filteredPolls = useMemo(() => {
    return polls.filter((poll) => {
      const matchesCategory = selectedCategory === 'All' || poll.category === selectedCategory;
      const matchesPollType = selectedPollType === 'all' || poll.pollType === selectedPollType;
      const matchesSearch = poll.question.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesPollType && matchesSearch;
    });
  }, [polls, selectedCategory, selectedPollType, searchQuery]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-linear-to-r from-primary-600 to-primary-700 py-12">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-white sm:text-4xl">
            Previous Polls
          </h1>
          <p className="mt-2 text-primary-100">
            Browse results from past AI-generated polls on current events
          </p>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          {/* Search */}
          <div className="relative w-full sm:w-96">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search polls..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          {/* Category Filter */}
          <div className="flex items-center gap-2 overflow-x-auto pb-2 sm:pb-0">
            <FunnelIcon className="h-5 w-5 text-gray-500 shrink-0" />
            <div className="flex gap-2">
              {categories.map((category) => (
                <button
                  key={category}
                  onClick={() => setSelectedCategory(category)}
                  className={`px-4 py-2 sm:px-3 sm:py-1 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                    selectedCategory === category
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                  }`}
                >
                  {category}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Poll Type Filter */}
        <div className="flex items-center gap-3 mt-4">
          <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Poll Type:</span>
          <div className="flex gap-2">
            <button
              onClick={() => setSelectedPollType('all')}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                selectedPollType === 'all'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setSelectedPollType('pulse')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                selectedPollType === 'pulse'
                  ? 'bg-linear-to-r from-rose-500 to-pink-500 text-white shadow-lg shadow-rose-500/25'
                  : 'bg-rose-100 dark:bg-rose-500/20 text-rose-700 dark:text-rose-400 hover:bg-rose-200 dark:hover:bg-rose-500/30'
              }`}
            >
              <HeartIcon className="h-4 w-4" />
              Pulse
            </button>
            <button
              onClick={() => setSelectedPollType('flash')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                selectedPollType === 'flash'
                  ? 'bg-linear-to-r from-amber-500 to-orange-500 text-white shadow-lg shadow-amber-500/25'
                  : 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400 hover:bg-amber-200 dark:hover:bg-amber-500/30'
              }`}
            >
              <BoltIcon className="h-4 w-4" />
              Flash
            </button>
            <button
              onClick={() => setSelectedPollType('standard')}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                selectedPollType === 'standard'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              Standard
            </button>
          </div>
        </div>
      </div>

      {/* Polls Grid */}
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pb-16">
        {isLoading ? (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 animate-pulse">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-4"></div>
                <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-4"></div>
                <div className="space-y-3">
                  {[1, 2, 3, 4].map((j) => (
                    <div key={j} className="h-12 bg-gray-200 dark:bg-gray-700 rounded"></div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : filteredPolls.length > 0 ? (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {filteredPolls.map((poll, index) => (
              <>
                <motion.div
                  key={poll.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                >
                  <PollCard poll={poll} />
                </motion.div>
                {/* Insert native ad after every 6th poll */}
                {(index + 1) % 6 === 0 && index < filteredPolls.length - 1 && (
                  <motion.div
                    key={`ad-${index}`}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: (index + 1) * 0.05 }}
                    className="md:col-span-2 lg:col-span-3"
                  >
                    <NativeAd placement="polls-grid" className="my-2" />
                  </motion.div>
                )}
              </>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <MagnifyingGlassIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
              No polls found
            </h3>
            <p className="mt-2 text-gray-500 dark:text-gray-400">
              Try adjusting your search or filter to find what you&apos;re looking for.
            </p>
            <button
              onClick={() => {
                setSearchQuery('');
                setSelectedCategory('All');
                setSelectedPollType('all');
              }}
              className="mt-4 inline-flex items-center gap-2 text-primary-600 hover:text-primary-700 font-medium"
            >
              <ArrowPathIcon className="h-4 w-4" />
              Reset filters
            </button>
          </div>
        )}
      </div>
    </div>
  );
}