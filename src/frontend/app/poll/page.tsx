'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams, usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { api, Poll, PollWithResults, VoteRequest } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import {
  ChartBarIcon,
  ClockIcon,
  UserGroupIcon,
  CheckCircleIcon,
  ArrowLeftIcon,
  SparklesIcon,
  PresentationChartBarIcon,
} from '@heroicons/react/24/outline';
import { CheckCircleIcon as CheckCircleSolidIcon } from '@heroicons/react/24/solid';
import { PollResults } from '@/components/polls/poll-results';
import { useToast } from '@/components/ui/toast';
import { SocialShare } from '@/components/ui/social-share';

function PollDetailContent() {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  
  // Support both /poll?id=xxx and /polls/xxx URL formats
  const getPollId = (): string | null => {
    // First check query param
    const queryId = searchParams.get('id');
    if (queryId) return queryId;
    
    // Then check if URL is /polls/xxx format (via navigation fallback)
    if (pathname?.startsWith('/polls/')) {
      const pathId = pathname.split('/polls/')[1]?.split('/')[0];
      if (pathId) return pathId;
    }
    
    return null;
  };
  
  const pollId = getPollId();
  
  const queryClient = useQueryClient();
  const { isAuthenticated, refreshUser } = useAuth();
  const { success } = useToast();
  const [selectedChoice, setSelectedChoice] = useState<string | null>(null);
  const [showResults, setShowResults] = useState(false);
  const [hasVoted, setHasVoted] = useState(false);
  const [showDetailedResults, setShowDetailedResults] = useState(false);

  // Fetch poll data (basic info for voting)
  const { data: poll, isLoading, error } = useQuery<Poll>({
    queryKey: ['poll', pollId],
    queryFn: () => api.getPoll(pollId!),
    staleTime: 30000,
    enabled: !!pollId,
  });

  // Fetch poll results (with vote counts) - enabled when hasVoted, showResults, or poll is closed
  const { data: pollResults, refetch: refetchResults } = useQuery<PollWithResults>({
    queryKey: ['poll-results', pollId],
    queryFn: () => api.getPollResults(pollId!),
    enabled: !!pollId && (hasVoted || showResults || (poll?.status !== 'active')),
    staleTime: 10000,
  });

  // Vote mutation
  const voteMutation = useMutation({
    mutationFn: (voteData: VoteRequest) => api.vote(pollId!, voteData),
    onSuccess: () => {
      setHasVoted(true);
      setShowResults(true);
      queryClient.invalidateQueries({ queryKey: ['poll', pollId] });
      queryClient.invalidateQueries({ queryKey: ['poll-results', pollId] });
      queryClient.invalidateQueries({ queryKey: ['user-points'] });
      refetchResults(); // Immediately fetch updated results
      // Refresh user in auth context to update nav bar points
      refreshUser();
      success('Vote recorded!', 'You earned +10 points for participating.');
    },
  });

  // Check if user has already voted via API
  useEffect(() => {
    const checkVoteStatus = async () => {
      if (poll && isAuthenticated && pollId) {
        try {
          const response = await api.checkVoteStatus(pollId);
          if (response.has_voted) {
            setHasVoted(true);
            setShowResults(true);
            setShowDetailedResults(true); // Show detailed results automatically for returning voters
          }
        } catch {
          // Fallback to localStorage if API fails
          const votedPolls = JSON.parse(localStorage.getItem('votedPolls') || '[]');
          if (votedPolls.includes(pollId)) {
            setHasVoted(true);
            setShowResults(true);
            setShowDetailedResults(true);
          }
        }
      }
    };
    checkVoteStatus();
  }, [poll, isAuthenticated, pollId]);

  const handleVote = () => {
    if (!selectedChoice || hasVoted || !pollId) return;
    
    voteMutation.mutate({
      choice_id: selectedChoice,
    });
    
    // Store in localStorage as backup
    const votedPolls = JSON.parse(localStorage.getItem('votedPolls') || '[]');
    if (!votedPolls.includes(pollId)) {
      votedPolls.push(pollId);
      localStorage.setItem('votedPolls', JSON.stringify(votedPolls));
    }
  };

  const formatTimeRemaining = (endTime: string) => {
    const end = new Date(endTime);
    const now = new Date();
    const diff = end.getTime() - now.getTime();
    
    if (diff <= 0) return 'Ended';
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    
    if (hours > 0) {
      return `${hours}h ${minutes}m left`;
    }
    return `${minutes}m left`;
  };

  const totalVotes = pollResults?.choices?.reduce((sum, c) => sum + (c.vote_count || 0), 0) || 0;

  // No poll ID provided
  if (!pollId) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">No poll specified</h2>
          <p className="text-gray-600 dark:text-gray-400 mb-4">Please select a poll from the list.</p>
          <Link
            href="/polls"
            className="inline-flex items-center text-blue-600 hover:text-blue-700 dark:text-blue-400"
          >
            <ArrowLeftIcon className="h-5 w-5 mr-2" />
            View all polls
          </Link>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !poll) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Poll not found</h2>
          <p className="text-gray-600 dark:text-gray-400 mb-4">This poll may have expired or doesn&apos;t exist.</p>
          <Link
            href="/polls"
            className="inline-flex items-center text-blue-600 hover:text-blue-700 dark:text-blue-400"
          >
            <ArrowLeftIcon className="h-5 w-5 mr-2" />
            Back to polls
          </Link>
        </div>
      </div>
    );
  }

  const displayData = pollResults || poll;
  const isActive = poll.status === 'active';
  const canVote = isActive && !hasVoted;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 py-8">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Back link */}
        <Link
          href="/polls"
          className="inline-flex items-center text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white mb-6 transition-colors"
        >
          <ArrowLeftIcon className="h-5 w-5 mr-2" />
          Back to polls
        </Link>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg overflow-hidden"
        >
          {/* Poll header */}
          <div className="p-6 border-b border-gray-200 dark:border-slate-700">
            <div className="flex items-start justify-between mb-4">
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                poll.category === 'politics' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300' :
                poll.category === 'technology' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300' :
                poll.category === 'sports' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' :
                poll.category === 'entertainment' ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300' :
                poll.category === 'business' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300' :
                'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
              }`}>
                {poll.category}
              </span>
              <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                <ClockIcon className="h-5 w-5 mr-1" />
                {formatTimeRemaining(poll.scheduled_end || poll.expires_at)}
              </div>
            </div>
            
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              {poll.question}
            </h1>
            
            {poll.ai_generated && (
              <div className="flex items-center text-sm text-purple-600 dark:text-purple-400 mb-4">
                <SparklesIcon className="h-4 w-4 mr-1" />
                AI-generated from current events
              </div>
            )}

            <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
              <div className="flex items-center">
                <UserGroupIcon className="h-5 w-5 mr-1" />
                {totalVotes.toLocaleString()} votes
              </div>
              <div className="flex items-center">
                <ChartBarIcon className="h-5 w-5 mr-1" />
                {displayData.choices?.length || 0} options
              </div>
            </div>
          </div>

          {/* Voting section */}
          <div className="p-6">
            <AnimatePresence mode="wait">
              {canVote ? (
                <motion.div
                  key="voting"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-4"
                >
                  {poll.choices?.map((choice) => (
                    <motion.button
                      key={choice.id}
                      onClick={() => setSelectedChoice(choice.id)}
                      className={`w-full p-4 rounded-xl border-2 text-left transition-all ${
                        selectedChoice === choice.id
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-gray-200 dark:border-slate-600 hover:border-gray-300 dark:hover:border-slate-500'
                      }`}
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-gray-900 dark:text-white">
                          {choice.text}
                        </span>
                        {selectedChoice === choice.id && (
                          <CheckCircleSolidIcon className="h-6 w-6 text-blue-500" />
                        )}
                      </div>
                    </motion.button>
                  ))}

                  <motion.button
                    onClick={handleVote}
                    disabled={!selectedChoice || voteMutation.isPending}
                    className={`w-full py-4 rounded-xl font-semibold text-lg transition-all ${
                      selectedChoice
                        ? 'bg-blue-600 hover:bg-blue-700 text-white'
                        : 'bg-gray-200 dark:bg-slate-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                    }`}
                    whileHover={selectedChoice ? { scale: 1.02 } : {}}
                    whileTap={selectedChoice ? { scale: 0.98 } : {}}
                  >
                    {voteMutation.isPending ? (
                      <span className="flex items-center justify-center">
                        <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        Submitting...
                      </span>
                    ) : (
                      'Cast Vote'
                    )}
                  </motion.button>
                </motion.div>
              ) : (
                <motion.div
                  key="results"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-4"
                >
                  {hasVoted && (
                    <div className="flex items-center justify-center text-green-600 dark:text-green-400 mb-4">
                      <CheckCircleIcon className="h-6 w-6 mr-2" />
                      <span className="font-medium">Your vote has been recorded!</span>
                    </div>
                  )}

                  {/* Show choice results with percentages */}
                  {displayData.choices?.map((choice) => {
                    const votes = (choice as { votes?: number }).votes || 0;
                    const percentage = totalVotes > 0 ? (votes / totalVotes) * 100 : 0;
                    
                    return (
                      <div key={choice.id} className="relative">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium text-gray-900 dark:text-white">
                            {choice.text}
                          </span>
                          <span className="text-sm text-gray-600 dark:text-gray-400">
                            {percentage.toFixed(1)}%
                          </span>
                        </div>
                        <div className="h-3 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${percentage}%` }}
                            transition={{ duration: 0.5, ease: 'easeOut' }}
                            className="h-full bg-linear-to-r from-blue-500 to-blue-600 rounded-full"
                          />
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          {votes.toLocaleString()} votes
                        </div>
                      </div>
                    );
                  })}

                  {/* Toggle Detailed Results Button */}
                  <button
                    onClick={() => setShowDetailedResults(!showDetailedResults)}
                    className="w-full py-3 mt-4 rounded-xl font-medium text-blue-600 dark:text-blue-400 border-2 border-blue-200 dark:border-blue-800 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors flex items-center justify-center"
                  >
                    <PresentationChartBarIcon className="h-5 w-5 mr-2" />
                    {showDetailedResults ? 'Hide' : 'Show'} Demographic Breakdown
                  </button>

                  {/* Detailed Results */}
                  <AnimatePresence>
                    {showDetailedResults && pollResults && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="overflow-hidden"
                      >
                        <PollResults 
                          pollId={pollId}
                          question={poll.question}
                          choices={pollResults.choices.map(c => ({
                            id: c.id,
                            text: c.text,
                            vote_count: c.vote_count || 0,
                            percentage: totalVotes > 0 ? Math.round((c.vote_count || 0) / totalVotes * 100) : 0
                          }))}
                          totalVotes={totalVotes}
                        />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Social Share */}
          <div className="p-6 border-t border-gray-200 dark:border-slate-700">
            <SocialShare
              content={{
                title: poll.question,
                text: "Share your opinion on TruePulse",
                url: typeof window !== 'undefined' ? `${window.location.origin}/poll?id=${pollId}` : `/poll?id=${pollId}`,
                hashtags: ['TruePulse', 'Opinion', poll.category?.replace(/\s+/g, '') || 'Vote'],
                pollId: pollId,
              }}
              variant="button"
              size="md"
            />
          </div>
        </motion.div>
      </div>
    </div>
  );
}

// Loading fallback for Suspense
function PollDetailLoading() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
    </div>
  );
}

// Main page component with Suspense boundary (required for useSearchParams in static export)
export default function PollPage() {
  return (
    <Suspense fallback={<PollDetailLoading />}>
      <PollDetailContent />
    </Suspense>
  );
}
