'use client';

import { use } from 'react';
import { useState, useEffect } from 'react';
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

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function PollDetailPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const pollId = resolvedParams.id;
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
    queryFn: () => api.getPoll(pollId),
    staleTime: 30000,
  });

  // Fetch poll results (with vote counts) - enabled when hasVoted, showResults, or poll is closed
  const { data: pollResults, refetch: refetchResults } = useQuery<PollWithResults>({
    queryKey: ['poll-results', pollId],
    queryFn: () => api.getPollResults(pollId),
    enabled: hasVoted || showResults || (poll?.status !== 'active'),
    staleTime: 10000,
  });

  // Vote mutation
  const voteMutation = useMutation({
    mutationFn: (voteData: VoteRequest) => api.vote(pollId, voteData),
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
      if (poll && isAuthenticated) {
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

  // For closed polls, always show results
  const isPollActive = poll?.is_active && poll?.status === 'active';
  const isPollClosed = poll ? (!isPollActive || new Date(poll.expires_at) < new Date()) : false;
  
  useEffect(() => {
    if (isPollClosed) {
      setShowResults(true);
      setShowDetailedResults(true);
    }
  }, [isPollClosed]);

  const handleVote = () => {
    if (!selectedChoice || !isAuthenticated) return;

    voteMutation.mutate({
      choice_id: selectedChoice,
    });

    // Store in localStorage
    const votedPolls = JSON.parse(localStorage.getItem('votedPolls') || '[]');
    votedPolls.push(pollId);
    localStorage.setItem('votedPolls', JSON.stringify(votedPolls));
  };

  const calculatePercentage = (votes: number, total: number) => {
    if (total === 0) return 0;
    return Math.round((votes / total) * 100);
  };

  const formatTimeRemaining = (endTime: string) => {
    const end = new Date(endTime);
    const now = new Date();
    const diff = end.getTime() - now.getTime();

    if (diff <= 0) return 'Ended';

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 24) {
      const days = Math.floor(hours / 24);
      return `${days}d ${hours % 24}h remaining`;
    }
    return `${hours}h ${minutes}m remaining`;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gradient-to-br dark:from-slate-900 dark:via-purple-900 dark:to-slate-900 flex items-center justify-center">
        <div className="animate-spin h-12 w-12 border-4 border-purple-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (error || !poll) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gradient-to-br dark:from-slate-900 dark:via-purple-900 dark:to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Poll not found</h1>
          <Link href="/" className="text-purple-600 dark:text-purple-400 hover:text-purple-500 dark:hover:text-purple-300">
            ← Back to home
          </Link>
        </div>
      </div>
    );
  }

  // Use pollResults for vote counts when available, otherwise fall back to poll
  const displayChoices = pollResults?.choices || poll.choices;
  const totalVotes = pollResults?.total_votes || displayChoices.reduce((sum, choice) => sum + (choice.vote_count || 0), 0);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gradient-to-br dark:from-slate-900 dark:via-purple-900 dark:to-slate-900 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Back Button */}
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-gray-600 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white transition-colors mb-8"
        >
          <ArrowLeftIcon className="h-5 w-5" />
          Back to polls
        </Link>

        {/* Poll Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white dark:bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-gray-200 dark:border-slate-700/50 overflow-hidden shadow-xl dark:shadow-2xl"
        >
          {/* Header */}
          <div className="p-6 border-b border-gray-200 dark:border-slate-700/50">
            <div className="flex items-start justify-between gap-4">
              <div>
                {poll.category && (
                  <span className="inline-flex items-center gap-1 px-3 py-1 bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-400 text-sm font-medium rounded-full mb-3">
                    <SparklesIcon className="h-4 w-4" />
                    {poll.category}
                  </span>
                )}
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{poll.question}</h1>
              </div>
              <SocialShare
                content={{
                  title: poll.question,
                  text: `Vote on: "${poll.question}" - Join the global conversation on TruePulse`,
                  url: typeof window !== 'undefined' ? window.location.href : `/polls/${pollId}`,
                  hashtags: ['TruePulse', 'GlobalOpinion', poll.category?.replace(/\s+/g, '') || 'Vote'],
                  pollId: pollId,
                }}
                variant="icon"
                size="md"
              />
            </div>

            {/* Meta info */}
            <div className="flex flex-wrap gap-4 mt-4 text-sm text-gray-500 dark:text-slate-400">
              <div className="flex items-center gap-1">
                <UserGroupIcon className="h-4 w-4" />
                <span>{totalVotes.toLocaleString()} votes</span>
              </div>
              <div className="flex items-center gap-1">
                <ClockIcon className="h-4 w-4" />
                <span>{poll.time_remaining_seconds ? formatTimeRemaining(poll.scheduled_end || poll.expires_at) : 'Ended'}</span>
              </div>
              {poll.ai_generated && (
                <div className="flex items-center gap-1 text-cyan-600 dark:text-cyan-400">
                  <SparklesIcon className="h-4 w-4" />
                  <span>AI Generated</span>
                </div>
              )}
            </div>
          </div>

          {/* Choices */}
          <div className="p-6 space-y-3">
            <AnimatePresence mode="wait">
              {displayChoices.map((choice, index) => {
                const percentage = calculatePercentage(choice.vote_count || 0, totalVotes);
                const isSelected = selectedChoice === choice.id;
                const isWinning = percentage === Math.max(...displayChoices.map(c => calculatePercentage(c.vote_count || 0, totalVotes)));

                return (
                  <motion.button
                    key={choice.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    onClick={() => !hasVoted && !showResults && isPollActive && setSelectedChoice(choice.id)}
                    disabled={hasVoted || showResults || !isPollActive}
                    className={`w-full relative overflow-hidden rounded-xl border transition-all ${
                      isSelected
                        ? 'border-purple-500 bg-purple-100 dark:bg-purple-500/20'
                        : 'border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-900/50 hover:border-gray-300 dark:hover:border-slate-600'
                    } ${(hasVoted || showResults || !isPollActive) ? 'cursor-default' : 'cursor-pointer'}`}
                  >
                    {/* Progress bar */}
                    {(showResults || hasVoted) && (
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${percentage}%` }}
                        transition={{ duration: 0.8, ease: 'easeOut' }}
                        className={`absolute inset-0 ${
                          isWinning ? 'bg-gradient-to-r from-purple-200 dark:from-purple-600/30 to-cyan-200 dark:to-cyan-600/30' : 'bg-gray-200 dark:bg-slate-700/30'
                        }`}
                      />
                    )}

                    <div className="relative flex items-center justify-between p-4">
                      <div className="flex items-center gap-3">
                        {/* Selection indicator */}
                        {hasVoted && isSelected ? (
                          <CheckCircleSolidIcon className="h-6 w-6 text-green-500" />
                        ) : (
                          <div
                            className={`h-6 w-6 rounded-full border-2 flex items-center justify-center transition-colors ${
                              isSelected ? 'border-purple-500 bg-purple-500' : 'border-gray-400 dark:border-slate-600'
                            }`}
                          >
                            {isSelected && <CheckCircleIcon className="h-4 w-4 text-white" />}
                          </div>
                        )}
                        <span className="text-gray-900 dark:text-white font-medium">{choice.text}</span>
                      </div>

                      {/* Results */}
                      {(showResults || hasVoted) && (
                        <motion.div
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          className="flex items-center gap-2"
                        >
                          <span className="text-gray-500 dark:text-slate-400 text-sm">{(choice.vote_count || 0).toLocaleString()}</span>
                          <span className={`font-bold ${isWinning ? 'text-cyan-600 dark:text-cyan-400' : 'text-gray-700 dark:text-slate-300'}`}>
                            {percentage}%
                          </span>
                        </motion.div>
                      )}
                    </div>
                  </motion.button>
                );
              })}
            </AnimatePresence>
          </div>

          {/* Actions */}
          <div className="p-6 pt-0">
            {isPollClosed ? (
              <div className="space-y-4">
                <div className="bg-gray-100 dark:bg-slate-900/50 rounded-xl p-4 text-center">
                  <p className="text-gray-600 dark:text-slate-400 font-medium">This poll has ended</p>
                  {totalVotes === 0 && (
                    <p className="text-sm text-gray-500 dark:text-slate-500 mt-1">No votes were recorded for this poll</p>
                  )}
                </div>
                
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setShowDetailedResults(!showDetailedResults)}
                  className="w-full py-3 px-4 bg-gradient-to-r from-gray-200 dark:from-slate-700 to-gray-300 dark:to-slate-600 text-gray-900 dark:text-white font-semibold rounded-xl hover:from-gray-300 dark:hover:from-slate-600 hover:to-gray-400 dark:hover:to-slate-500 transition-all flex items-center justify-center gap-2"
                >
                  <PresentationChartBarIcon className="h-5 w-5" />
                  {showDetailedResults ? 'Hide Demographic Insights' : 'View Demographic Insights'}
                </motion.button>
              </div>
            ) : !isAuthenticated ? (
              <div className="bg-gray-100 dark:bg-slate-900/50 rounded-xl p-4 text-center">
                <p className="text-gray-600 dark:text-slate-400 mb-3">Sign in to vote on this poll</p>
                <Link
                  href="/login"
                  className="inline-block px-6 py-2 bg-gradient-to-r from-purple-600 to-cyan-600 text-white font-semibold rounded-lg hover:from-purple-500 hover:to-cyan-500 transition-colors"
                >
                  Sign in to vote
                </Link>
              </div>
            ) : hasVoted ? (
              <div className="space-y-4">
                <div className="bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/30 rounded-xl p-4 text-center">
                  <div className="flex items-center justify-center gap-2 text-green-600 dark:text-green-400">
                    <CheckCircleSolidIcon className="h-5 w-5" />
                    <span className="font-medium">Your vote has been recorded!</span>
                  </div>
                  <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">+10 points earned</p>
                </div>
                
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setShowDetailedResults(!showDetailedResults)}
                  className="w-full py-3 px-4 bg-gradient-to-r from-gray-200 dark:from-slate-700 to-gray-300 dark:to-slate-600 text-gray-900 dark:text-white font-semibold rounded-xl hover:from-gray-300 dark:hover:from-slate-600 hover:to-gray-400 dark:hover:to-slate-500 transition-all flex items-center justify-center gap-2"
                >
                  <PresentationChartBarIcon className="h-5 w-5" />
                  {showDetailedResults ? 'Hide Demographic Insights' : 'View Demographic Insights'}
                </motion.button>
              </div>
            ) : (
              <div className="space-y-3">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleVote}
                  disabled={!selectedChoice || voteMutation.isPending}
                  className="w-full py-3 px-4 bg-gradient-to-r from-purple-600 to-cyan-600 text-white font-semibold rounded-xl hover:from-purple-500 hover:to-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  {voteMutation.isPending ? (
                    <div className="flex items-center justify-center">
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Recording vote...
                    </div>
                  ) : (
                    'Submit Vote'
                  )}
                </motion.button>

                <button
                  onClick={() => setShowResults(!showResults)}
                  className="w-full py-2 text-gray-500 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white text-sm transition-colors"
                >
                  <ChartBarIcon className="h-4 w-4 inline mr-1" />
                  {showResults ? 'Hide results' : 'Peek at results'}
                </button>
              </div>
            )}
          </div>
        </motion.div>

        {/* Privacy Notice */}
        <p className="text-center text-sm text-gray-500 dark:text-slate-500 mt-6">
          🔒 Your vote is anonymous and cannot be traced back to you
        </p>

        {/* Detailed Results with Demographics */}
        {showDetailedResults && (hasVoted || isPollClosed) && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mt-8"
          >
            <PollResults
              pollId={pollId}
              question={poll.question}
              choices={displayChoices.map(c => ({
                id: c.id,
                text: c.text,
                vote_count: c.vote_count || 0,
                percentage: totalVotes > 0 ? Math.round((c.vote_count || 0) / totalVotes * 100) : 0
              }))}
              totalVotes={totalVotes}
            />
          </motion.div>
        )}
      </div>
    </div>
  );
}
