'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock, Users, CheckCircle, ChevronRight, Lock, Loader2, Sparkles, Zap, Heart } from 'lucide-react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { api } from '@/lib/api';
import { Celebration, PointsPopup } from '@/components/ui/celebration';
import { TrustBadge } from '@/components/ui/trust-badge';
import { SocialShare } from '@/components/ui/social-share';

interface PollChoice {
  id: string;
  text: string;
  votePercentage: number;
}

interface Poll {
  id: string;
  question: string;
  choices: PollChoice[];
  totalVotes: number;
  category: string;
  sourceEvent?: string;
  expiresAt: Date;
  pollType?: 'pulse' | 'flash' | 'standard';
  isClosed?: boolean;
}

interface PollCardProps {
  poll: Poll;
  showVoteButton?: boolean;
}

// Poll type badge component
function PollTypeBadge({ pollType }: { pollType?: string }) {
  if (!pollType || pollType === 'standard') return null;
  
  if (pollType === 'pulse') {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-bold bg-linear-to-r from-rose-500 to-pink-500 text-white shadow-lg shadow-rose-500/25">
        <Heart className="h-4 w-4 fill-current" />
        Pulse Poll
      </span>
    );
  }
  
  if (pollType === 'flash') {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-bold bg-linear-to-r from-amber-500 to-orange-500 text-white shadow-lg shadow-amber-500/25 animate-pulse">
        <Zap className="h-4 w-4 fill-current" />
        Flash Poll
      </span>
    );
  }
  
  return null;
}

// Poll type header banner
function PollTypeHeader({ pollType }: { pollType?: string }) {
  if (!pollType || pollType === 'standard') return null;
  
  if (pollType === 'pulse') {
    return (
      <div className="absolute top-0 left-0 right-0 h-1.5 bg-linear-to-r from-rose-500 via-pink-500 to-rose-500 rounded-t-2xl" />
    );
  }
  
  if (pollType === 'flash') {
    return (
      <div className="absolute top-0 left-0 right-0 h-1.5 bg-linear-to-r from-amber-500 via-orange-500 to-amber-500 rounded-t-2xl animate-pulse" />
    );
  }
  
  return null;
}

export function PollCard({ poll, showVoteButton = true }: PollCardProps) {
  const { isAuthenticated } = useAuth();
  const [selectedChoice, setSelectedChoice] = useState<string | null>(null);
  const [hasVoted, setHasVoted] = useState(false);
  const [, setIsCheckingVoteStatus] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeLeft, setTimeLeft] = useState<string>('');
  const [showCelebration, setShowCelebration] = useState(false);
  const [showPoints, setShowPoints] = useState(false);
  const [earnedPoints, setEarnedPoints] = useState(10);

  // Check if user has already voted on this poll
  useEffect(() => {
    const checkVoteStatus = async () => {
      if (!isAuthenticated) {
        setIsCheckingVoteStatus(false);
        return;
      }
      
      try {
        const status = await api.checkVoteStatus(poll.id);
        setHasVoted(status.has_voted);
      } catch (err) {
        // If the API fails, assume not voted (user can try to vote and will get error if already voted)
        console.error('Failed to check vote status:', err);
      } finally {
        setIsCheckingVoteStatus(false);
      }
    };
    
    checkVoteStatus();
  }, [poll.id, isAuthenticated]);

  useEffect(() => {
    const calculateTimeRemaining = () => {
      const now = new Date();
      const diff = poll.expiresAt.getTime() - now.getTime();
      
      if (diff <= 0) {
        return 'Closed';
      }
      
      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);
      
      if (hours > 0) {
        return `${hours}h ${minutes}m remaining`;
      } else if (minutes > 0) {
        return `${minutes}m ${seconds}s remaining`;
      } else {
        return `${seconds}s remaining`;
      }
    };

    // Set initial value
    setTimeLeft(calculateTimeRemaining());

    // Update every second
    const interval = setInterval(() => {
      setTimeLeft(calculateTimeRemaining());
    }, 1000);

    return () => clearInterval(interval);
  }, [poll.expiresAt]);

  const handleVote = async () => {
    if (!selectedChoice || !isAuthenticated || isSubmitting) return;
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      const result = await api.vote(poll.id, { choice_id: selectedChoice });
      setHasVoted(true);
      
      // Trigger celebrations
      setEarnedPoints(result.points_earned || 10);
      setShowCelebration(true);
      setTimeout(() => setShowPoints(true), 300);
    } catch (err) {
      console.error('Vote failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to submit vote');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Check if poll is closed (either from prop or by checking expiry time)
  const isPollClosed = poll.isClosed || timeLeft === 'Closed';
  
  // Show results if user has voted OR if poll is closed
  const showResults = hasVoted || isPollClosed;
  
  // Non-authenticated users can view but not interact with choices (only if poll is open)
  const canInteract = isAuthenticated && !hasVoted && !isPollClosed;
  const isUrgent = timeLeft.includes('m') && !timeLeft.includes('h') && !isPollClosed;

  return (
    <>
      {/* Celebration effects */}
      <Celebration 
        trigger={showCelebration} 
        variant="sparkles" 
        onComplete={() => setShowCelebration(false)} 
      />
      <PointsPopup 
        points={earnedPoints} 
        trigger={showPoints} 
        onComplete={() => setShowPoints(false)} 
      />
      
      <motion.div 
        className={`group bg-white dark:bg-gray-800 rounded-2xl shadow-md hover:shadow-xl transition-all duration-300 p-6 relative overflow-hidden ${
          poll.pollType === 'pulse' ? 'ring-2 ring-rose-500/20' : 
          poll.pollType === 'flash' ? 'ring-2 ring-amber-500/20' : ''
        }`}
        whileHover={{ y: -2 }}
        layout
      >
        {/* Poll type colored header bar */}
        <PollTypeHeader pollType={poll.pollType} />
        
        {/* Subtle gradient overlay on hover */}
        <div className="absolute inset-0 bg-linear-to-br from-primary-500/0 to-accent-500/0 group-hover:from-primary-500/5 group-hover:to-accent-500/5 transition-all duration-300 rounded-2xl pointer-events-none" />
        
        {/* Header */}
        <div className="relative flex items-start justify-between mb-4">
          <div className="flex items-center gap-2 flex-wrap">
            <PollTypeBadge pollType={poll.pollType} />
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-primary-100 text-primary-800 dark:bg-primary-900/50 dark:text-primary-200">
              {poll.category}
            </span>
            <TrustBadge variant="anonymous" size="sm" showLabel={false} />
          </div>
          <motion.div 
            className={`flex items-center text-sm ${
              isUrgent 
                ? 'text-warm-600 dark:text-warm-400 font-medium' 
                : 'text-gray-500 dark:text-gray-400'
            }`}
            animate={isUrgent ? { scale: [1, 1.05, 1] } : {}}
            transition={{ duration: 1, repeat: isUrgent ? Infinity : 0 }}
          >
            <Clock className={`h-4 w-4 mr-1 ${isUrgent ? 'text-warm-500' : ''}`} />
            {timeLeft}
          </motion.div>
        </div>

        {/* Question */}
        <h3 className="relative text-lg font-semibold text-gray-900 dark:text-white mb-4 leading-relaxed">
          {poll.question}
        </h3>

        {/* Source Event */}
        {poll.sourceEvent && (
          <p className="relative text-sm text-gray-500 dark:text-gray-400 mb-4 flex items-center gap-1">
            <Sparkles className="h-3 w-3 text-primary-400" />
            Based on: {poll.sourceEvent}
          </p>
        )}

        {/* Choices */}
        <div className="relative space-y-3 mb-4">
          <AnimatePresence mode="wait">
            {poll.choices.map((choice, index) => (
              <motion.div
                key={choice.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className={`relative rounded-xl border-2 transition-all duration-200 ${
                  canInteract ? 'cursor-pointer' : 'cursor-default'
                } ${
                  selectedChoice === choice.id
                    ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30 shadow-md'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                } ${showResults ? 'bg-gray-50 dark:bg-gray-800/50' : ''}`}
                onClick={() => canInteract && setSelectedChoice(choice.id)}
                whileHover={canInteract ? { scale: 1.01 } : {}}
                whileTap={canInteract ? { scale: 0.99 } : {}}
              >
                <div className="p-4 flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <motion.div
                      className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors ${
                        selectedChoice === choice.id
                          ? 'border-primary-500 bg-primary-500'
                          : 'border-gray-300 dark:border-gray-600'
                      }`}
                      animate={selectedChoice === choice.id ? { scale: [1, 1.2, 1] } : {}}
                      transition={{ duration: 0.2 }}
                    >
                      {selectedChoice === choice.id && (
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          transition={{ type: 'spring', stiffness: 500 }}
                        >
                          <CheckCircle className="w-3 h-3 text-white" />
                        </motion.div>
                      )}
                    </motion.div>
                    <span className="text-gray-900 dark:text-white font-medium">{choice.text}</span>
                  </div>
                  {showResults && (
                    <motion.span 
                      className="text-sm font-bold text-primary-600 dark:text-primary-400"
                      initial={{ opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.3 + index * 0.1 }}
                    >
                      {choice.votePercentage}%
                    </motion.span>
                  )}
                </div>
                
                {/* Progress bar (shown after voting or when closed) */}
                {showResults && (
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${choice.votePercentage}%` }}
                    transition={{ duration: 0.8, ease: 'easeOut', delay: 0.2 }}
                    className="absolute bottom-0 left-0 h-1.5 bg-linear-to-r from-primary-500 to-primary-400 rounded-b-xl"
                  />
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        {/* Error message */}
        <AnimatePresence>
          {error && (
            <motion.div 
              className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Footer */}
        <div className="relative flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
              <Users className="h-4 w-4 mr-1.5" />
              <motion.span
                key={poll.totalVotes}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
              >
                {poll.totalVotes.toLocaleString()}
              </motion.span>
              <span className="ml-1">votes</span>
            </div>
            
            {/* Share Button */}
            <SocialShare
              content={{
                title: poll.question,
                text: `Vote on: "${poll.question}" - Join the global conversation on TruePulse`,
                url: typeof window !== 'undefined' ? `${window.location.origin}/poll?id=${poll.id}` : `/poll?id=${poll.id}`,
                hashtags: ['TruePulse', 'GlobalOpinion', poll.category.replace(/\s+/g, '')],
                pollId: poll.id,
              }}
              variant="icon"
              size="sm"
            />
            {/* Live indicator */}
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-trust-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-trust-500" />
            </span>
          </div>
          
          {/* Show sign in prompt for non-authenticated users on open polls only */}
          {showVoteButton && !isAuthenticated && !isPollClosed && (
            <Link
              href="/login"
              className="inline-flex items-center px-4 py-2.5 border border-transparent text-sm font-medium rounded-xl text-white bg-linear-to-r from-primary-600 to-primary-700 hover:from-primary-700 hover:to-primary-800 shadow-md hover:shadow-lg transition-all"
            >
              <Lock className="mr-1.5 h-4 w-4" />
              Sign in to vote
            </Link>
          )}
          
          {/* Show vote button for authenticated users who haven't voted on open polls */}
          {showVoteButton && isAuthenticated && !hasVoted && !isPollClosed && (
            <motion.button
              onClick={handleVote}
              disabled={!selectedChoice || isSubmitting}
              className="inline-flex items-center px-5 py-2.5 border border-transparent text-sm font-medium rounded-xl text-white bg-linear-to-r from-primary-600 to-primary-700 hover:from-primary-700 hover:to-primary-800 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed shadow-md hover:shadow-lg transition-all"
              whileHover={selectedChoice ? { scale: 1.02 } : {}}
              whileTap={selectedChoice ? { scale: 0.98 } : {}}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  Submit Vote
                  <ChevronRight className="ml-1 h-4 w-4" />
                </>
              )}
            </motion.button>
          )}
          
          {/* Show results link after voting or when closed */}
          {showResults && (
            <motion.div
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <Link
                href={`/poll?id=${poll.id}`}
                className="inline-flex items-center text-primary-600 hover:text-primary-700 dark:text-primary-400 text-sm font-medium group"
              >
                View full results 
                <ChevronRight className="ml-1 h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </Link>
            </motion.div>
          )}
        </div>
        
        {/* Success state overlay */}
        <AnimatePresence>
          {hasVoted && showCelebration && (
            <motion.div
              className="absolute inset-0 bg-trust-500/10 rounded-2xl pointer-events-none"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            />
          )}
        </AnimatePresence>
      </motion.div>
    </>
  );
}
