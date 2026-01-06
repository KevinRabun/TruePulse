'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { PollCard } from '@/components/polls/poll-card';
import { api, type Poll, type PollType } from '@/lib/api';
import { HeartIcon, BoltIcon } from '@heroicons/react/24/outline';

interface DisplayPoll {
  id: string;
  question: string;
  choices: { id: string; text: string; votePercentage: number }[];
  totalVotes: number;
  category: string;
  sourceEvent?: string;
  sourceEventUrl?: string;
  expiresAt: Date;
  pollType?: PollType;
  isClosed?: boolean;
}

function transformPoll(poll: Poll, isClosed = false): DisplayPoll {
  const totalVotes = poll.total_votes || 0;
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
    sourceEventUrl: poll.source_event_url,
    expiresAt: new Date(poll.expires_at),
    pollType: poll.poll_type,
    isClosed: isClosed || new Date(poll.expires_at) < new Date(),
  };
}

export function FeaturedPolls() {
  const [pulsePoll, setPulsePoll] = useState<DisplayPoll | null>(null);
  const [flashPoll, setFlashPoll] = useState<DisplayPoll | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchPolls = async () => {
      try {
        // Fetch current polls first, fall back to previous if not available
        const [currentPulse, currentFlash] = await Promise.all([
          api.getCurrentPulsePoll(),
          api.getCurrentFlashPoll(),
        ]);
        
        // Set pulse poll - use current if available, otherwise get previous
        if (currentPulse) {
          setPulsePoll(transformPoll(currentPulse));
        } else {
          const previousPulse = await api.getPreviousPulsePoll();
          if (previousPulse) {
            setPulsePoll(transformPoll(previousPulse, true));
          }
        }
        
        // Set flash poll - use current if available, otherwise get previous
        if (currentFlash) {
          setFlashPoll(transformPoll(currentFlash));
        } else {
          const previousFlash = await api.getPreviousFlashPoll();
          if (previousFlash) {
            setFlashPoll(transformPoll(previousFlash, true));
          }
        }
      } catch (error) {
        console.error('Failed to fetch polls:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchPolls();
    
    // Refresh polls every minute
    const interval = setInterval(fetchPolls, 60000);
    return () => clearInterval(interval);
  }, []);

  if (isLoading) {
    return (
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
              Today&apos;s Polls
            </h2>
            <p className="mt-2 text-gray-600 dark:text-gray-400">
              AI-generated unbiased questions from today&apos;s current events
            </p>
          </div>
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 animate-pulse">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-4"></div>
            <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-4"></div>
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-12 bg-gray-200 dark:bg-gray-700 rounded"></div>
              ))}
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 animate-pulse">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-4"></div>
            <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-4"></div>
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-12 bg-gray-200 dark:bg-gray-700 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </section>
    );
  }

  const hasPolls = pulsePoll || flashPoll;

  if (!hasPolls) {
    return (
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
              Today&apos;s Polls
            </h2>
            <p className="mt-2 text-gray-600 dark:text-gray-400">
              No polls available right now. Check back soon!
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
            Today&apos;s Polls
          </h2>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            AI-generated unbiased questions from today&apos;s current events
          </p>
        </div>
        <Link
          href="/polls"
          className="text-primary-600 hover:text-primary-700 font-medium"
        >
          View previous polls →
        </Link>
      </div>
      
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Pulse Poll */}
        {pulsePoll && (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <HeartIcon className="h-6 w-6 text-rose-500" />
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                {pulsePoll.isClosed ? 'Latest Pulse Poll' : 'Daily Pulse Poll'}
              </h3>
              {!pulsePoll.isClosed && (
                <span className="px-2 py-1 text-xs font-medium bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-400 rounded-full">
                  8am-8pm ET
                </span>
              )}
              {pulsePoll.isClosed && (
                <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400 rounded-full">
                  Closed
                </span>
              )}
            </div>
            <PollCard poll={pulsePoll} />
          </div>
        )}

        {/* Flash Poll */}
        {flashPoll && (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <BoltIcon className="h-6 w-6 text-amber-500" />
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                {flashPoll.isClosed ? 'Latest Flash Poll' : 'Flash Poll'}
              </h3>
              {!flashPoll.isClosed && (
                <span className="px-2 py-1 text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400 rounded-full animate-pulse">
                  1 Hour Only!
                </span>
              )}
              {flashPoll.isClosed && (
                <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400 rounded-full">
                  Closed
                </span>
              )}
            </div>
            <PollCard poll={flashPoll} />
          </div>
        )}
      </div>
    </section>
  );
}
