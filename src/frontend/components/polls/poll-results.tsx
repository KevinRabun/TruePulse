'use client';

import { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { api, DemographicBreakdown as APIDemographicBreakdown } from '@/lib/api';
import {
  ChartBarIcon,
  ChartPieIcon,
  UserGroupIcon,
  AcademicCapIcon,
  BriefcaseIcon,
  GlobeAltIcon,
  MapPinIcon,
  ScaleIcon,
  UsersIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  MinusIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

interface Choice {
  id: string;
  text: string;
  vote_count: number;
  percentage: number;
}

interface DemographicBreakdown {
  category: string;
  segments: {
    name: string;
    votes: number;
    choices: { choice_id: string; choice_text: string; percentage: number; count: number }[];
  }[];
}

interface PollResultsProps {
  pollId: string;
  question: string;
  choices: Choice[];
  totalVotes: number;
  demographicBreakdowns?: DemographicBreakdown[];
}

const categoryIcons: Record<string, React.ReactNode> = {
  age_range: <UsersIcon className="h-5 w-5" />,
  gender: <UserGroupIcon className="h-5 w-5" />,
  country: <GlobeAltIcon className="h-5 w-5" />,
  state_province: <MapPinIcon className="h-5 w-5" />,
  city: <MapPinIcon className="h-5 w-5" />,
  region: <MapPinIcon className="h-5 w-5" />,
  education_level: <AcademicCapIcon className="h-5 w-5" />,
  employment_status: <BriefcaseIcon className="h-5 w-5" />,
  political_leaning: <ScaleIcon className="h-5 w-5" />,
};

const categoryLabels: Record<string, string> = {
  age_range: 'Age Range',
  gender: 'Gender',
  country: 'Country',
  state_province: 'State/Province',
  city: 'City',
  region: 'Region',
  education_level: 'Education Level',
  employment_status: 'Employment Status',
  political_leaning: 'Political Leaning',
  industry: 'Industry',
};

// Color palette for choices
const choiceColors = [
  { bg: 'bg-purple-500', text: 'text-purple-400', bar: 'from-purple-600 to-purple-400' },
  { bg: 'bg-cyan-500', text: 'text-cyan-400', bar: 'from-cyan-600 to-cyan-400' },
  { bg: 'bg-amber-500', text: 'text-amber-400', bar: 'from-amber-600 to-amber-400' },
  { bg: 'bg-emerald-500', text: 'text-emerald-400', bar: 'from-emerald-600 to-emerald-400' },
  { bg: 'bg-rose-500', text: 'text-rose-400', bar: 'from-rose-600 to-rose-400' },
  { bg: 'bg-indigo-500', text: 'text-indigo-400', bar: 'from-indigo-600 to-indigo-400' },
];

export function PollResults({ pollId, question, choices, totalVotes, demographicBreakdowns }: PollResultsProps) {
  const [selectedDemographic, setSelectedDemographic] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'bars' | 'comparison'>('bars');
  
  // Fetch real demographics from API
  const { data: demographicsData, isLoading: demographicsLoading } = useQuery({
    queryKey: ['poll-demographics', pollId],
    queryFn: () => api.getPollDemographics(pollId),
    staleTime: 30000,
  });

  // Transform API response to component format
  const demographics = useMemo(() => {
    if (demographicBreakdowns) return demographicBreakdowns;
    if (!demographicsData?.breakdowns?.length) return [];
    
    return demographicsData.breakdowns.map(b => ({
      category: b.category,
      segments: b.segments.map(s => ({
        name: s.name,
        votes: s.votes,
        choices: s.choices.map(c => ({
          choice_id: choices.find(ch => ch.text === c.choice_text)?.id || '',
          choice_text: c.choice_text,
          percentage: c.percentage,
          count: c.count,
        })),
      })),
    }));
  }, [demographicBreakdowns, demographicsData, choices]);
  
  const hasDemographicData = demographics.length > 0;

  const selectedDemo = demographics.find(d => d.category === selectedDemographic);

  // Calculate which choices are trending up/down in selected demographic vs overall
  const getTrend = (choiceId: string, segmentPercentage: number) => {
    const overallChoice = choices.find(c => c.id === choiceId);
    if (!overallChoice) return 'neutral';
    const diff = segmentPercentage - overallChoice.percentage;
    if (diff > 5) return 'up';
    if (diff < -5) return 'down';
    return 'neutral';
  };

  return (
    <div className="space-y-8">
      {/* Overall Results */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white dark:bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-gray-200 dark:border-slate-700/50 p-6"
      >
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-500/20 rounded-lg">
              <ChartBarIcon className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">Overall Results</h2>
              <p className="text-sm text-gray-500 dark:text-slate-400">{totalVotes.toLocaleString()} total votes</p>
            </div>
          </div>
        </div>

        {/* Results Bars */}
        <div className="space-y-4">
          {choices.map((choice, index) => {
            const colorSet = choiceColors[index % choiceColors.length];
            const isWinning = choice.percentage === Math.max(...choices.map(c => c.percentage));
            
            return (
              <div key={choice.id} className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${colorSet.bg}`} />
                    <span className="text-gray-900 dark:text-white font-medium">{choice.text}</span>
                    {isWinning && (
                      <span className="px-2 py-0.5 bg-yellow-100 dark:bg-yellow-500/20 text-yellow-700 dark:text-yellow-400 text-xs rounded-full">
                        Leading
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-gray-500 dark:text-slate-400 text-sm">{choice.vote_count.toLocaleString()} votes</span>
                    <span className={`font-bold ${isWinning ? 'text-yellow-600 dark:text-yellow-400' : colorSet.text}`}>
                      {choice.percentage}%
                    </span>
                  </div>
                </div>
                <div className="h-3 bg-gray-200 dark:bg-slate-700/50 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${choice.percentage}%` }}
                    transition={{ duration: 1, ease: 'easeOut', delay: index * 0.1 }}
                    className={`h-full bg-gradient-to-r ${colorSet.bar} rounded-full`}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </motion.div>

      {/* Demographic Filter */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-white dark:bg-slate-800/50 backdrop-blur-xl rounded-2xl border border-gray-200 dark:border-slate-700/50 p-6"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-cyan-100 dark:bg-cyan-500/20 rounded-lg">
            <ChartPieIcon className="h-6 w-6 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Demographic Insights</h2>
            <p className="text-sm text-gray-500 dark:text-slate-400">See how different groups voted</p>
          </div>
        </div>

        {/* Loading state */}
        {demographicsLoading && (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin h-8 w-8 border-4 border-purple-500 border-t-transparent rounded-full"></div>
          </div>
        )}

        {/* No demographic data state */}
        {!demographicsLoading && !hasDemographicData && (
          <div className="text-center py-8">
            <ExclamationTriangleIcon className="h-12 w-12 text-gray-400 dark:text-slate-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-700 dark:text-slate-300 mb-2">No Demographic Data Yet</h3>
            <p className="text-gray-500 dark:text-slate-400 text-sm max-w-md mx-auto">
              Demographic insights will appear once users with profile information participate in this poll.
              Update your profile to contribute anonymous demographic data.
            </p>
          </div>
        )}

        {/* Demographic data available */}
        {!demographicsLoading && hasDemographicData && (
          <>
            {/* Demographic Category Selector */}
            <div className="flex flex-wrap gap-2 mb-6">
              <button
                onClick={() => setSelectedDemographic(null)}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  selectedDemographic === null
                    ? 'bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-400 border border-purple-300 dark:border-purple-500/50'
                    : 'bg-gray-100 dark:bg-slate-700/50 text-gray-600 dark:text-slate-400 border border-gray-200 dark:border-slate-600/50 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                All Demographics
              </button>
              {demographics.map(demo => (
                <button
                  key={demo.category}
                  onClick={() => setSelectedDemographic(demo.category)}
                  className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    selectedDemographic === demo.category
                      ? 'bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-400 border border-purple-300 dark:border-purple-500/50'
                      : 'bg-gray-100 dark:bg-slate-700/50 text-gray-600 dark:text-slate-400 border border-gray-200 dark:border-slate-600/50 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  {categoryIcons[demo.category]}
                  {categoryLabels[demo.category] || demo.category}
            </button>
          ))}
        </div>

        {/* View Mode Toggle */}
        {selectedDemographic && (
          <div className="flex items-center gap-2 mb-6">
            <span className="text-sm text-gray-500 dark:text-slate-400">View:</span>
            <button
              onClick={() => setViewMode('bars')}
              className={`px-3 py-1 rounded text-sm ${
                viewMode === 'bars'
                  ? 'bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-400'
                  : 'text-gray-500 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Breakdown
            </button>
            <button
              onClick={() => setViewMode('comparison')}
              className={`px-3 py-1 rounded text-sm ${
                viewMode === 'comparison'
                  ? 'bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-400'
                  : 'text-gray-500 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Comparison
            </button>
          </div>
        )}

        <AnimatePresence mode="wait">
          {selectedDemographic === null ? (
            /* Overview Grid */
            <motion.div
              key="overview"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
            >
              {demographics.map(demo => {
                // Find the most distinctive result for this demographic
                const mostDistinctive = demo.segments.reduce((prev, curr) => {
                  const maxDiff = Math.max(...curr.choices.map(c => {
                    const overall = choices.find(oc => oc.id === c.choice_id);
                    return overall ? Math.abs(c.percentage - overall.percentage) : 0;
                  }));
                  const prevMaxDiff = Math.max(...prev.choices.map(c => {
                    const overall = choices.find(oc => oc.id === c.choice_id);
                    return overall ? Math.abs(c.percentage - overall.percentage) : 0;
                  }));
                  return maxDiff > prevMaxDiff ? curr : prev;
                });

                const topChoice = mostDistinctive.choices.reduce((prev, curr) => 
                  curr.percentage > prev.percentage ? curr : prev
                );

                return (
                  <button
                    key={demo.category}
                    onClick={() => setSelectedDemographic(demo.category)}
                    className="bg-gray-100 dark:bg-slate-900/50 rounded-xl p-4 border border-gray-200 dark:border-slate-700/50 hover:border-purple-400 dark:hover:border-purple-500/50 transition-all text-left group"
                  >
                    <div className="flex items-center gap-2 mb-3">
                      <div className="text-gray-500 dark:text-slate-400 group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors">
                        {categoryIcons[demo.category]}
                      </div>
                      <h3 className="font-semibold text-gray-900 dark:text-white">
                        {categoryLabels[demo.category] || demo.category}
                      </h3>
                    </div>
                    <p className="text-sm text-gray-500 dark:text-slate-400 mb-2">
                      Notable finding:
                    </p>
                    <p className="text-sm text-cyan-600 dark:text-cyan-400">
                      <span className="font-semibold">{mostDistinctive.name}</span> voters favor{' '}
                      <span className="font-semibold">&quot;{topChoice.choice_text}&quot;</span>
                      {' '}({topChoice.percentage}%)
                    </p>
                  </button>
                );
              })}
            </motion.div>
          ) : (
            /* Detailed Breakdown */
            <motion.div
              key={selectedDemographic}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-6"
            >
              {viewMode === 'bars' ? (
                /* Bar Chart View */
                selectedDemo?.segments.map((segment, segIndex) => (
                  <div key={segment.name} className="bg-gray-100 dark:bg-slate-900/50 rounded-xl p-4 border border-gray-200 dark:border-slate-700/50">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="font-semibold text-gray-900 dark:text-white">{segment.name}</h4>
                      <span className="text-sm text-gray-500 dark:text-slate-400">{segment.votes.toLocaleString()} votes</span>
                    </div>
                    <div className="space-y-3">
                      {segment.choices.map((choice, choiceIndex) => {
                        const colorSet = choiceColors[choiceIndex % choiceColors.length];
                        const trend = getTrend(choice.choice_id, choice.percentage);
                        const isTopChoice = choice.percentage === Math.max(...segment.choices.map(c => c.percentage));
                        
                        return (
                          <div key={choice.choice_id} className="space-y-1">
                            <div className="flex items-center justify-between text-sm">
                              <div className="flex items-center gap-2">
                                <div className={`w-2 h-2 rounded-full ${colorSet.bg}`} />
                                <span className="text-gray-700 dark:text-slate-300">{choice.choice_text}</span>
                              </div>
                              <div className="flex items-center gap-2">
                                {trend === 'up' && (
                                  <ArrowTrendingUpIcon className="h-4 w-4 text-emerald-500 dark:text-emerald-400" />
                                )}
                                {trend === 'down' && (
                                  <ArrowTrendingDownIcon className="h-4 w-4 text-rose-500 dark:text-rose-400" />
                                )}
                                {trend === 'neutral' && (
                                  <MinusIcon className="h-4 w-4 text-gray-400 dark:text-slate-500" />
                                )}
                                <span className={`font-medium ${isTopChoice ? 'text-cyan-600 dark:text-cyan-400' : 'text-gray-500 dark:text-slate-400'}`}>
                                  {choice.percentage}%
                                </span>
                              </div>
                            </div>
                            <div className="h-2 bg-gray-200 dark:bg-slate-700/50 rounded-full overflow-hidden">
                              <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${choice.percentage}%` }}
                                transition={{ duration: 0.8, delay: segIndex * 0.05 + choiceIndex * 0.02 }}
                                className={`h-full bg-gradient-to-r ${colorSet.bar} rounded-full`}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))
              ) : (
                /* Comparison Table View */
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200 dark:border-slate-700/50">
                        <th className="text-left py-3 px-4 text-gray-500 dark:text-slate-400 font-medium">Segment</th>
                        {choices.map((choice, index) => (
                          <th key={choice.id} className="text-center py-3 px-4">
                            <div className="flex items-center justify-center gap-2">
                              <div className={`w-2 h-2 rounded-full ${choiceColors[index % choiceColors.length].bg}`} />
                              <span className="text-gray-700 dark:text-slate-300 text-sm">{choice.text}</span>
                            </div>
                          </th>
                        ))}
                        <th className="text-right py-3 px-4 text-gray-500 dark:text-slate-400 font-medium">Votes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {/* Overall row */}
                      <tr className="border-b border-gray-200 dark:border-slate-700/50 bg-purple-50 dark:bg-purple-500/10">
                        <td className="py-3 px-4 font-medium text-purple-700 dark:text-purple-400">Overall</td>
                        {choices.map(choice => (
                          <td key={choice.id} className="text-center py-3 px-4 text-gray-900 dark:text-white font-semibold">
                            {choice.percentage}%
                          </td>
                        ))}
                        <td className="text-right py-3 px-4 text-gray-500 dark:text-slate-400">
                          {totalVotes.toLocaleString()}
                        </td>
                      </tr>
                      {selectedDemo?.segments.map(segment => (
                        <tr key={segment.name} className="border-b border-gray-100 dark:border-slate-700/30 hover:bg-gray-50 dark:hover:bg-slate-700/20">
                          <td className="py-3 px-4 text-gray-900 dark:text-white">{segment.name}</td>
                          {segment.choices.map((choice, index) => {
                            const trend = getTrend(choice.choice_id, choice.percentage);
                            const overall = choices.find(c => c.id === choice.choice_id);
                            const diff = overall ? choice.percentage - overall.percentage : 0;
                            
                            return (
                              <td key={choice.choice_id} className="text-center py-3 px-4">
                                <div className="flex items-center justify-center gap-1">
                                  <span className={
                                    diff > 5 ? 'text-emerald-600 dark:text-emerald-400' :
                                    diff < -5 ? 'text-rose-600 dark:text-rose-400' :
                                    'text-gray-700 dark:text-slate-300'
                                  }>
                                    {choice.percentage}%
                                  </span>
                                  {diff !== 0 && (
                                    <span className={`text-xs ${diff > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                                      ({diff > 0 ? '+' : ''}{diff})
                                    </span>
                                  )}
                                </div>
                              </td>
                            );
                          })}
                          <td className="text-right py-3 px-4 text-gray-500 dark:text-slate-400 text-sm">
                            {segment.votes.toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Legend */}
        {hasDemographicData && (
          <div className="mt-6 pt-4 border-t border-gray-200 dark:border-slate-700/50">
            <p className="text-xs text-gray-500 dark:text-slate-500 flex items-center gap-4">
              <span className="flex items-center gap-1">
                <ArrowTrendingUpIcon className="h-3 w-3 text-emerald-500 dark:text-emerald-400" />
                Above average
              </span>
              <span className="flex items-center gap-1">
                <ArrowTrendingDownIcon className="h-3 w-3 text-rose-500 dark:text-rose-400" />
                Below average
              </span>
              <span className="flex items-center gap-1">
                <MinusIcon className="h-3 w-3 text-gray-400 dark:text-slate-500" />
              Near average
            </span>
          </p>
        </div>
        )}
          </>
        )}
      </motion.div>

      {/* Key Insights */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="bg-gradient-to-r from-purple-100 dark:from-purple-900/50 to-cyan-100 dark:to-cyan-900/50 backdrop-blur-xl rounded-2xl border border-purple-200 dark:border-purple-500/30 p-6"
      >
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <span className="text-2xl">💡</span>
          Key Insights
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white/60 dark:bg-slate-900/50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-purple-700 dark:text-purple-400 mb-2">Consensus Level</h4>
            <p className="text-gray-900 dark:text-white">
              {(() => {
                const sortedChoices = [...choices].sort((a, b) => b.percentage - a.percentage);
                const topDiff = sortedChoices[0].percentage - (sortedChoices[1]?.percentage || 0);
                const totalDiff = sortedChoices[0].percentage - (sortedChoices[sortedChoices.length - 1]?.percentage || 0);
                
                if (totalVotes < 10) {
                  return 'Not enough votes yet to determine consensus';
                } else if (topDiff > 30) {
                  return `Strong consensus - "${sortedChoices[0].text}" leads by ${topDiff}%`;
                } else if (topDiff < 10) {
                  return `Divided opinion - top choices are within ${topDiff}% of each other`;
                } else {
                  return `Moderate agreement - "${sortedChoices[0].text}" leads with ${sortedChoices[0].percentage}%`;
                }
              })()}
            </p>
          </div>
          <div className="bg-white/60 dark:bg-slate-900/50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-cyan-700 dark:text-cyan-400 mb-2">Participation</h4>
            <p className="text-gray-900 dark:text-white">
              {totalVotes === 1 
                ? 'You are the first voter! More insights will appear as others participate.'
                : totalVotes < 10
                ? `${totalVotes} votes so far. Insights will become more meaningful with more participants.`
                : hasDemographicData
                ? 'Demographic breakdowns available - see how different groups voted above.'
                : `${totalVotes} votes recorded. Add your demographic info in your profile to contribute to demographic insights.`
              }
            </p>
          </div>
        </div>
      </motion.div>

      {/* Privacy Notice */}
      <p className="text-center text-xs text-gray-500 dark:text-slate-500">
        🔒 All demographic data is anonymized and aggregated. Individual votes cannot be traced.
      </p>
    </div>
  );
}
